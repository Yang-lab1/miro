from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text

from app.api.schemas.realtime import RealtimeTurnRespondRequest
from app.core.config import get_settings
from app.models.simulation import (
    RealtimeSession,
    RealtimeSessionAlert,
    RealtimeSessionTurn,
    Simulation,
    VoiceProfileCatalog,
)
from app.models.user import User
from app.modules.realtime import service as realtime_service
from app.services.current_actor import CurrentActor

BACKEND_DIR = Path(__file__).resolve().parents[1]

COUNTRY_SETUP = {
    "Japan": {
        "meetingType": "first_introduction",
        "goal": "establish_trust_before_pricing",
        "durationMinutes": 10,
        "voiceStyle": "formal_measured",
        "voiceProfileId": "vp_japan_female_01",
    },
    "Germany": {
        "meetingType": "commercial_alignment",
        "goal": "clarify_process_and_risk_ownership",
        "durationMinutes": 12,
        "voiceStyle": "direct_structured",
        "voiceProfileId": "vp_germany_male_01",
    },
}


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_simulation(client, country_key: str, *, full_setup: bool) -> dict:
    payload = {"countryKey": country_key}
    if full_setup:
        payload |= COUNTRY_SETUP[country_key]
        payload["constraints"] = "Keep the conversation calm and structured."

    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200
    return response.json()


def _create_strategy_ready_simulation(client, country_key: str = "Japan") -> dict:
    created = _create_simulation(client, country_key, full_setup=True)
    generated = client.post(f"/api/v1/simulations/{created['simulationId']}/strategy")
    assert generated.status_code == 200
    return generated.json()


def _create_realtime_session(
    client,
    simulation_id: str,
    *,
    transport: str | None = None,
) -> dict:
    payload = {"simulationId": simulation_id}
    if transport is not None:
        payload["transport"] = transport

    response = client.post("/api/v1/realtime/sessions", json=payload)
    assert response.status_code == 200
    return response.json()


def _create_active_realtime_session(client, country_key: str = "Japan") -> tuple[dict, dict]:
    simulation = _create_strategy_ready_simulation(client, country_key)
    created = _create_realtime_session(client, simulation["simulationId"])
    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200
    return simulation, started.json()


def _respond_turn(
    client,
    session_id: str,
    *,
    input_mode: str = "text",
    source_text: str,
    language: str | None = None,
):
    payload = {"inputMode": input_mode, "sourceText": source_text}
    if language is not None:
        payload["language"] = language
    return client.post(f"/api/v1/realtime/sessions/{session_id}/turns/respond", json=payload)


def _get_realtime_session_record(db_session, session_id: str) -> RealtimeSession:
    db_session.expire_all()
    record = db_session.scalar(select(RealtimeSession).where(RealtimeSession.id == session_id))
    assert record is not None
    return record


def _expire_realtime_session(db_session, session_id: str) -> None:
    record = _get_realtime_session_record(db_session, session_id)
    record.launch_expires_at = datetime.now(tz=UTC) - timedelta(minutes=1)
    db_session.commit()


def _set_provider_mode(monkeypatch, mode: str) -> None:
    monkeypatch.setenv("REALTIME_PROVIDER_MODE", mode)
    get_settings.cache_clear()


def _set_mock_remote_status(db_session, session_id: str, status: str) -> None:
    record = _get_realtime_session_record(db_session, session_id)
    payload = dict(record.provider_payload_json or {})
    payload["simulatedProviderStatus"] = status
    record.provider_payload_json = payload
    db_session.commit()


def test_create_realtime_session_success_with_default_webrtc(client):
    simulation = _create_strategy_ready_simulation(client)

    payload = _create_realtime_session(client, simulation["simulationId"])

    assert payload["simulationId"] == simulation["simulationId"]
    assert payload["status"] == "pending"
    assert payload["transport"] == "webrtc"
    assert payload["voiceProfileId"] == "vp_japan_female_01"
    assert payload["setupRevision"] == 1
    assert payload["strategyForSetupRevision"] == 1
    assert payload["launch"]["mode"] == "stub"
    assert payload["launch"]["transport"] == "webrtc"
    assert payload["launch"]["fallbackTransport"] == "websocket"
    assert payload["launch"]["sessionToken"]
    assert payload["launch"]["connectUrl"] is None
    assert payload["startedAt"] is None
    assert payload["endedAt"] is None


def test_stub_provider_create_persists_internal_provider_fields(client, db_session):
    simulation = _create_strategy_ready_simulation(client)

    payload = _create_realtime_session(client, simulation["simulationId"])

    record = _get_realtime_session_record(db_session, payload["sessionId"])
    assert record.provider_mode == "stub"
    assert record.provider_status == "created"
    assert record.provider_session_id is None
    assert record.provider_payload_json == {"kind": "stub"}


def test_create_realtime_session_with_websocket_transport(client):
    simulation = _create_strategy_ready_simulation(client)

    payload = _create_realtime_session(
        client,
        simulation["simulationId"],
        transport="websocket",
    )

    assert payload["transport"] == "websocket"
    assert payload["launch"]["transport"] == "websocket"
    assert payload["launch"]["fallbackTransport"] is None


def test_mock_remote_provider_create_returns_connect_url_and_persists_fields(
    client,
    db_session,
    monkeypatch,
):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)

    payload = _create_realtime_session(client, simulation["simulationId"])

    assert payload["launch"]["mode"] == "mock_remote"
    assert payload["launch"]["connectUrl"] is not None
    record = _get_realtime_session_record(db_session, payload["sessionId"])
    assert record.provider_mode == "mock_remote"
    assert record.provider_status == "created"
    assert record.provider_session_id is not None
    assert record.provider_payload_json["simulatedProviderStatus"] == "created"
    assert record.provider_payload_json["providerSessionId"] == record.provider_session_id


def test_create_realtime_session_is_idempotent_for_matching_pending(client):
    simulation = _create_strategy_ready_simulation(client)

    first = _create_realtime_session(client, simulation["simulationId"])
    second = _create_realtime_session(client, simulation["simulationId"])

    assert second["sessionId"] == first["sessionId"]
    assert second["launch"]["sessionToken"] == first["launch"]["sessionToken"]


def test_create_realtime_session_is_idempotent_for_active_even_when_transport_differs(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "active"

    created_again = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation["simulationId"], "transport": "websocket"},
    )
    assert created_again.status_code == 200
    assert created_again.json()["sessionId"] == created["sessionId"]
    assert created_again.json()["status"] == "active"
    assert created_again.json()["transport"] == "webrtc"


def test_create_realtime_session_fails_when_learning_precheck_is_not_ready(client):
    simulation = _create_strategy_ready_simulation(client, "Germany")

    response = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation["simulationId"]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "learning_precheck_failed"


def test_create_realtime_session_fails_when_strategy_is_missing(client):
    simulation = _create_simulation(client, "Japan", full_setup=True)

    response = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation["simulationId"]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "simulation_strategy_missing"


def test_create_realtime_session_fails_when_strategy_revision_is_outdated(client, db_session):
    simulation = _create_strategy_ready_simulation(client)

    record = db_session.scalar(
        select(Simulation).where(Simulation.id == simulation["simulationId"])
    )
    assert record is not None
    record.setup_revision += 1
    db_session.commit()

    response = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation["simulationId"]},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "simulation_strategy_outdated"


def test_create_realtime_session_replaces_expired_pending_with_new_session(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    original = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, original["sessionId"])

    replacement = _create_realtime_session(client, simulation["simulationId"])

    assert replacement["sessionId"] != original["sessionId"]
    old_record = _get_realtime_session_record(db_session, original["sessionId"])
    assert old_record.session_status == "failed"
    assert old_record.status_reason == "launch_expired"
    assert old_record.ended_at is not None


def test_create_realtime_session_replaces_pending_when_transport_changes(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    original = _create_realtime_session(client, simulation["simulationId"])

    replacement = _create_realtime_session(
        client,
        simulation["simulationId"],
        transport="websocket",
    )

    assert replacement["sessionId"] != original["sessionId"]
    assert replacement["transport"] == "websocket"
    old_record = _get_realtime_session_record(db_session, original["sessionId"])
    assert old_record.session_status == "failed"
    assert old_record.status_reason == "superseded_transport"
    assert old_record.ended_at is not None


def test_create_realtime_session_replaces_pending_when_setup_revision_changes(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    original = _create_realtime_session(client, simulation["simulationId"])

    updated = client.patch(
        f"/api/v1/simulations/{simulation['simulationId']}",
        json={"constraints": "Use a more conservative opening."},
    )
    assert updated.status_code == 200
    regenerated = client.post(f"/api/v1/simulations/{simulation['simulationId']}/strategy")
    assert regenerated.status_code == 200
    assert regenerated.json()["setupRevision"] == 2

    replacement = _create_realtime_session(client, simulation["simulationId"])

    assert replacement["sessionId"] != original["sessionId"]
    assert replacement["setupRevision"] == 2
    old_record = _get_realtime_session_record(db_session, original["sessionId"])
    assert old_record.session_status == "failed"
    assert old_record.status_reason == "superseded_setup_revision"


def test_create_realtime_session_replaces_pending_when_strategy_changes(
    client,
    db_session,
):
    simulation = _create_strategy_ready_simulation(client)
    original = _create_realtime_session(client, simulation["simulationId"])

    original_record = _get_realtime_session_record(db_session, original["sessionId"])
    original_record.strategy_for_setup_revision = 0
    db_session.commit()

    replacement = _create_realtime_session(client, simulation["simulationId"])

    assert replacement["sessionId"] != original["sessionId"]
    old_record = _get_realtime_session_record(db_session, original["sessionId"])
    assert old_record.session_status == "failed"
    assert old_record.status_reason == "superseded_strategy_revision"


def test_get_realtime_session_returns_snapshot(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    fetched = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}")

    assert fetched.status_code == 200
    assert fetched.json()["sessionId"] == created["sessionId"]
    assert fetched.json()["launch"] == created["launch"]


def test_get_realtime_session_marks_expired_pending_as_failed(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    fetched = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}")

    assert fetched.status_code == 200
    assert fetched.json()["status"] == "failed"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.session_status == "failed"
    assert record.status_reason == "launch_expired"
    assert record.provider_status == "failed"


def test_start_realtime_session_activates_pending_session_and_is_idempotent(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200
    started_payload = started.json()
    assert started_payload["status"] == "active"
    assert started_payload["startedAt"] is not None

    started_again = client.post(
        f"/api/v1/realtime/sessions/{created['sessionId']}/start"
    )
    assert started_again.status_code == 200
    assert started_again.json()["status"] == "active"
    assert started_again.json()["startedAt"] == started_payload["startedAt"]
    assert started_again.json()["launch"] == started_payload["launch"]


def test_start_sets_provider_status_connected(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")

    assert started.status_code == 200
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.provider_status == "connected"


def test_start_realtime_session_returns_launch_expired_for_expired_pending(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    response = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_launch_expired"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.session_status == "failed"
    assert record.status_reason == "launch_expired"


def test_start_realtime_session_rejects_ended_session(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")
    assert ended.status_code == 200

    response = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_startable"


def test_start_realtime_session_rejects_non_expired_failed_session(client):
    simulation = _create_strategy_ready_simulation(client)
    original = _create_realtime_session(client, simulation["simulationId"])

    replacement = _create_realtime_session(
        client,
        simulation["simulationId"],
        transport="websocket",
    )
    assert replacement["sessionId"] != original["sessionId"]

    response = client.post(f"/api/v1/realtime/sessions/{original['sessionId']}/start")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_startable"


def test_end_realtime_session_succeeds_for_pending_and_is_idempotent(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")
    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"
    assert ended.json()["endedAt"] is not None

    ended_again = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")
    assert ended_again.status_code == 200
    assert ended_again.json()["status"] == "ended"
    assert ended_again.json()["endedAt"] == ended.json()["endedAt"]

    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.status_reason == "manually_ended"
    assert record.provider_status == "closed"


def test_end_realtime_session_succeeds_for_active(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200

    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")
    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"

    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.session_status == "ended"
    assert record.status_reason == "manually_ended"
    assert record.provider_status == "closed"


def test_end_realtime_session_returns_failed_snapshot_for_failed_session(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")

    assert ended.status_code == 200
    assert ended.json()["status"] == "failed"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.session_status == "failed"
    assert record.status_reason == "launch_expired"
    assert record.provider_status == "failed"


def test_sync_maps_mock_remote_closed_to_session_ended(client, db_session, monkeypatch):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _set_mock_remote_status(db_session, created["sessionId"], "closed")

    synced = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/sync")

    assert synced.status_code == 200
    assert synced.json()["status"] == "ended"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.provider_status == "closed"
    assert record.session_status == "ended"
    assert record.ended_at is not None


def test_sync_maps_mock_remote_failed_to_session_failed(client, db_session, monkeypatch):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _set_mock_remote_status(db_session, created["sessionId"], "failed")

    synced = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/sync")

    assert synced.status_code == 200
    assert synced.json()["status"] == "failed"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.provider_status == "failed"
    assert record.session_status == "failed"
    assert record.ended_at is not None


def test_get_applies_runtime_sync_for_mock_remote_closed_session(client, db_session, monkeypatch):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _set_mock_remote_status(db_session, created["sessionId"], "closed")

    fetched = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}")

    assert fetched.status_code == 200
    assert fetched.json()["status"] == "ended"


def test_start_applies_runtime_sync_for_mock_remote_failed_session(
    client,
    db_session,
    monkeypatch,
):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _set_mock_remote_status(db_session, created["sessionId"], "failed")

    response = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_startable"


def test_end_applies_runtime_sync_for_mock_remote_closed_session(client, db_session, monkeypatch):
    _set_provider_mode(monkeypatch, "mock_remote")
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _set_mock_remote_status(db_session, created["sessionId"], "closed")

    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")

    assert ended.status_code == 200
    assert ended.json()["status"] == "ended"
    record = _get_realtime_session_record(db_session, created["sessionId"])
    assert record.provider_status == "closed"


def test_realtime_session_is_actor_scoped_for_get_start_end_and_sync(client, db_session):
    other_user = User(email="other-realtime@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()

    voice_profile = db_session.scalar(
        select(VoiceProfileCatalog).where(
            VoiceProfileCatalog.voice_profile_id == "vp_japan_female_01"
        )
    )
    assert voice_profile is not None

    simulation = Simulation(
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        simulation_status="strategy_ready",
        setup_revision=1,
        strategy_payload_json={"templateKey": "seed"},
        strategy_for_setup_revision=1,
    )
    db_session.add(simulation)
    db_session.flush()

    realtime_session = RealtimeSession(
        simulation_id=simulation.id,
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        setup_revision=1,
        strategy_for_setup_revision=1,
        transport="webrtc",
        session_status="pending",
        status_reason=None,
        launch_payload_json={
            "mode": "stub",
            "transport": "webrtc",
            "sessionToken": "other-token",
            "connectUrl": None,
            "fallbackTransport": "websocket",
            "expiresAt": (datetime.now(tz=UTC) + timedelta(minutes=15)).isoformat(),
        },
        launch_expires_at=datetime.now(tz=UTC) + timedelta(minutes=15),
    )
    db_session.add(realtime_session)
    db_session.commit()

    get_response = client.get(f"/api/v1/realtime/sessions/{realtime_session.id}")
    start_response = client.post(f"/api/v1/realtime/sessions/{realtime_session.id}/start")
    end_response = client.post(f"/api/v1/realtime/sessions/{realtime_session.id}/end")
    sync_response = client.post(f"/api/v1/realtime/sessions/{realtime_session.id}/sync")

    assert get_response.status_code == 404
    assert get_response.json()["error"]["code"] == "realtime_session_not_found"
    assert start_response.status_code == 404
    assert start_response.json()["error"]["code"] == "realtime_session_not_found"
    assert end_response.status_code == 404
    assert end_response.json()["error"]["code"] == "realtime_session_not_found"
    assert sync_response.status_code == 404
    assert sync_response.json()["error"]["code"] == "realtime_session_not_found"


def test_active_session_can_respond_and_persist_turn_pair(client, db_session):
    _, realtime_session = _create_active_realtime_session(client)

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        input_mode="speech_stub",
        source_text="   We need a clearer rollout owner before next week.   ",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sessionId"] == realtime_session["sessionId"]
    assert payload["turnCount"] == 2
    assert payload["userTurn"]["speaker"] == "user"
    assert payload["userTurn"]["inputMode"] == "speech_stub"
    assert (
        payload["userTurn"]["sourceText"]
        == "   We need a clearer rollout owner before next week.   "
    )
    assert (
        payload["userTurn"]["normalizedText"]
        == "We need a clearer rollout owner before next week."
    )
    assert payload["userTurn"]["language"] == "en"
    assert payload["userTurn"]["parentTurnId"] is None
    assert payload["assistantTurn"]["speaker"] == "assistant"
    assert payload["assistantTurn"]["inputMode"] is None
    assert payload["assistantTurn"]["parentTurnId"] == payload["userTurn"]["turnId"]

    db_turns = db_session.scalars(
        select(RealtimeSessionTurn)
        .where(RealtimeSessionTurn.session_id == realtime_session["sessionId"])
        .order_by(RealtimeSessionTurn.turn_index.asc())
    ).all()
    assert [turn.turn_index for turn in db_turns] == [1, 2]
    assert db_turns[0].speaker == "user"
    assert db_turns[1].speaker == "assistant"


def test_respond_increments_turn_indexes_strictly(client):
    _, realtime_session = _create_active_realtime_session(client)

    first = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We should align on owners and approval steps before rollout.",
    )
    second = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We also need a realistic timeline and one accountable process owner.",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["userTurn"]["turnIndex"] == 1
    assert first.json()["assistantTurn"]["turnIndex"] == 2
    assert second.json()["userTurn"]["turnIndex"] == 3
    assert second.json()["assistantTurn"]["turnIndex"] == 4
    assert second.json()["turnCount"] == 4


def test_get_turns_returns_ordered_transcript(client):
    _, realtime_session = _create_active_realtime_session(client)
    _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We should clarify ownership before rollout.",
    )
    _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We also need to agree on the approval process and exact timeline.",
    )

    response = client.get(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/turns")

    assert response.status_code == 200
    transcript = response.json()
    assert [turn["turnIndex"] for turn in transcript] == [1, 2, 3, 4]
    assert transcript[0]["speaker"] == "user"
    assert transcript[1]["speaker"] == "assistant"
    assert transcript[2]["speaker"] == "user"
    assert transcript[3]["parentTurnId"] == transcript[2]["turnId"]


def test_get_alerts_returns_alerts_in_reverse_created_order(client):
    _, realtime_session = _create_active_realtime_session(client)
    first = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="Too short",
    )
    second = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "We always guarantee a 100% outcome with no risk because our team never "
            "misses delivery commitments."
        ),
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = client.get(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/alerts")

    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) == 2
    assert alerts[0]["issueKey"] == "overclaiming"
    assert alerts[1]["issueKey"] == "underdeveloped_answer"


def test_short_answer_triggers_underdeveloped_answer(client, db_session):
    _, realtime_session = _create_active_realtime_session(client)

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="Need alignment first.",
    )

    assert response.status_code == 200
    payload = response.json()
    assert [alert["issueKey"] for alert in payload["alerts"]] == ["underdeveloped_answer"]
    db_alerts = db_session.scalars(
        select(RealtimeSessionAlert).where(
            RealtimeSessionAlert.session_id == realtime_session["sessionId"]
        )
    ).all()
    assert len(db_alerts) == 1
    assert db_alerts[0].turn_id == payload["userTurn"]["turnId"]


def test_japan_first_introduction_pricing_words_trigger_premature_pricing_push(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "Before anything else, we should discuss price and budget "
            "expectations for this introduction."
        ),
    )

    assert response.status_code == 200
    issue_keys = [alert["issueKey"] for alert in response.json()["alerts"]]
    assert "premature_pricing_push" in issue_keys


def test_absolute_claims_trigger_overclaiming(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "We always guarantee a 100% result with no risk because our process "
            "never fails in enterprise delivery."
        ),
    )

    assert response.status_code == 200
    issue_keys = [alert["issueKey"] for alert in response.json()["alerts"]]
    assert issue_keys == ["overclaiming"]


def test_single_respond_caps_alerts_at_two(client):
    _, realtime_session = _create_active_realtime_session(client, "Japan")

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="price discount guarantee 100%",
    )

    assert response.status_code == 200
    alerts = response.json()["alerts"]
    assert len(alerts) == 2
    assert [alert["issueKey"] for alert in alerts] == [
        "underdeveloped_answer",
        "premature_pricing_push",
    ]


def test_pending_session_cannot_respond(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    response = _respond_turn(
        client,
        created["sessionId"],
        source_text="We should continue.",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_active"


def test_ended_session_cannot_respond(client):
    _, realtime_session = _create_active_realtime_session(client)
    ended = client.post(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/end")
    assert ended.status_code == 200

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="We should continue.",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_active"


def test_failed_session_cannot_respond(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    response = _respond_turn(
        client,
        created["sessionId"],
        source_text="We should continue.",
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "realtime_session_not_active"


def test_realtime_turn_endpoints_are_actor_scoped(client, db_session):
    other_user = User(email="other-turns@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()

    voice_profile = db_session.scalar(
        select(VoiceProfileCatalog).where(
            VoiceProfileCatalog.voice_profile_id == "vp_japan_female_01"
        )
    )
    assert voice_profile is not None

    simulation = Simulation(
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        simulation_status="strategy_ready",
        setup_revision=1,
        strategy_payload_json={"templateKey": "seed"},
        strategy_for_setup_revision=1,
    )
    db_session.add(simulation)
    db_session.flush()

    realtime_session = RealtimeSession(
        simulation_id=simulation.id,
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        setup_revision=1,
        strategy_for_setup_revision=1,
        transport="webrtc",
        session_status="active",
        status_reason=None,
        provider_mode="stub",
        provider_status="connected",
        provider_payload_json={"kind": "stub"},
        launch_payload_json={
            "mode": "stub",
            "transport": "webrtc",
            "sessionToken": "other-turn-token",
            "connectUrl": None,
            "fallbackTransport": "websocket",
            "expiresAt": (datetime.now(tz=UTC) + timedelta(minutes=15)).isoformat(),
        },
        launch_expires_at=datetime.now(tz=UTC) + timedelta(minutes=15),
        started_at=datetime.now(tz=UTC),
    )
    db_session.add(realtime_session)
    db_session.commit()

    turns_response = client.get(f"/api/v1/realtime/sessions/{realtime_session.id}/turns")
    alerts_response = client.get(f"/api/v1/realtime/sessions/{realtime_session.id}/alerts")
    respond_response = _respond_turn(
        client,
        realtime_session.id,
        source_text="Need a follow-up.",
    )

    assert turns_response.status_code == 404
    assert turns_response.json()["error"]["code"] == "realtime_session_not_found"
    assert alerts_response.status_code == 404
    assert alerts_response.json()["error"]["code"] == "realtime_session_not_found"
    assert respond_response.status_code == 404
    assert respond_response.json()["error"]["code"] == "realtime_session_not_found"


def test_respond_updates_session_summary_fields(client):
    _, realtime_session = _create_active_realtime_session(client)

    response = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="price discount guarantee 100%",
    )
    assert response.status_code == 200

    summary = client.get(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/summary")

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["sessionId"] == realtime_session["sessionId"]
    assert payload["status"] == "active"
    assert payload["turnCount"] == 2
    assert payload["alertCount"] == 2
    assert payload["lastAlertSeverity"] == "high"
    assert payload["lastUserTurnAt"] is not None
    assert payload["lastAssistantTurnAt"] is not None


def test_summary_preserves_last_alert_severity_when_new_respond_has_no_alerts(client):
    _, realtime_session = _create_active_realtime_session(client)

    first = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="price discount guarantee 100%",
    )
    assert first.status_code == 200

    second = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "We should clarify the onboarding process and named owners before "
            "the follow up meeting next week."
        ),
    )
    assert second.status_code == 200
    assert second.json()["alerts"] == []

    summary = client.get(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/summary")

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["turnCount"] == 4
    assert payload["alertCount"] == 2
    assert payload["lastAlertSeverity"] == "high"


def test_summary_updates_last_alert_severity_when_new_alert_arrives(client):
    _, realtime_session = _create_active_realtime_session(client)

    first = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text="Need alignment first.",
    )
    assert first.status_code == 200

    second = _respond_turn(
        client,
        realtime_session["sessionId"],
        source_text=(
            "Before pricing, we should discuss budget expectations for this "
            "introduction in more detail."
        ),
    )
    assert second.status_code == 200

    summary = client.get(f"/api/v1/realtime/sessions/{realtime_session['sessionId']}/summary")

    assert summary.status_code == 200
    payload = summary.json()
    assert payload["alertCount"] == 2
    assert payload["lastAlertSeverity"] == "high"


def test_get_realtime_session_summary_returns_stable_fields(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    response = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}/summary")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "sessionId",
        "status",
        "transport",
        "countryKey",
        "meetingType",
        "goal",
        "durationMinutes",
        "voiceStyle",
        "voiceProfileId",
        "setupRevision",
        "strategyForSetupRevision",
        "turnCount",
        "alertCount",
        "lastAlertSeverity",
        "lastUserTurnAt",
        "lastAssistantTurnAt",
        "startedAt",
        "endedAt",
        "createdAt",
        "updatedAt",
    }


def test_summary_is_readable_for_pending_active_and_ended_sessions(client):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])

    pending_summary = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}/summary")
    assert pending_summary.status_code == 200
    assert pending_summary.json()["status"] == "pending"

    started = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/start")
    assert started.status_code == 200
    active_summary = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}/summary")
    assert active_summary.status_code == 200
    assert active_summary.json()["status"] == "active"

    ended = client.post(f"/api/v1/realtime/sessions/{created['sessionId']}/end")
    assert ended.status_code == 200
    ended_summary = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}/summary")
    assert ended_summary.status_code == 200
    assert ended_summary.json()["status"] == "ended"


def test_summary_applies_runtime_sync_for_failed_pending_session(client, db_session):
    simulation = _create_strategy_ready_simulation(client)
    created = _create_realtime_session(client, simulation["simulationId"])
    _expire_realtime_session(db_session, created["sessionId"])

    response = client.get(f"/api/v1/realtime/sessions/{created['sessionId']}/summary")

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_summary_is_actor_scoped(client, db_session):
    other_user = User(email="other-summary@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()

    voice_profile = db_session.scalar(
        select(VoiceProfileCatalog).where(
            VoiceProfileCatalog.voice_profile_id == "vp_japan_female_01"
        )
    )
    assert voice_profile is not None

    simulation = Simulation(
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        simulation_status="strategy_ready",
        setup_revision=1,
        strategy_payload_json={"templateKey": "seed"},
        strategy_for_setup_revision=1,
    )
    db_session.add(simulation)
    db_session.flush()

    realtime_session = RealtimeSession(
        simulation_id=simulation.id,
        user_id=other_user.id,
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        setup_revision=1,
        strategy_for_setup_revision=1,
        transport="webrtc",
        session_status="pending",
        launch_payload_json={
            "mode": "stub",
            "transport": "webrtc",
            "sessionToken": "other-summary-token",
            "connectUrl": None,
            "fallbackTransport": "websocket",
            "expiresAt": (datetime.now(tz=UTC) + timedelta(minutes=15)).isoformat(),
        },
        launch_expires_at=datetime.now(tz=UTC) + timedelta(minutes=15),
    )
    db_session.add(realtime_session)
    db_session.commit()

    response = client.get(f"/api/v1/realtime/sessions/{realtime_session.id}/summary")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "realtime_session_not_found"


def test_turn_index_allocator_reserves_non_overlapping_ranges_across_sessions(client):
    _, realtime_session = _create_active_realtime_session(client)

    from app.db.session import get_session_factory

    session_factory = get_session_factory()
    session_a = session_factory()
    session_b = session_factory()
    verifier = session_factory()
    try:
        record_a = session_a.scalar(
            select(RealtimeSession).where(RealtimeSession.id == realtime_session["sessionId"])
        )
        record_b = session_b.scalar(
            select(RealtimeSession).where(RealtimeSession.id == realtime_session["sessionId"])
        )
        assert record_a is not None
        assert record_b is not None

        first_pair = realtime_service._reserve_turn_index_pair(session_a, record_a)
        session_a.commit()
        second_pair = realtime_service._reserve_turn_index_pair(session_b, record_b)
        session_b.commit()

        verified = verifier.scalar(
            select(RealtimeSession).where(RealtimeSession.id == realtime_session["sessionId"])
        )
        assert verified is not None
        assert first_pair == (1, 2)
        assert second_pair == (3, 4)
        assert verified.next_turn_index == 5
    finally:
        session_a.close()
        session_b.close()
        verifier.close()


def test_phase8_migration_backfills_summary_and_next_turn_index(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'phase8-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("DEMO_USER_EMAIL", "demo@miro.local")

    from app.db.session import get_session_factory, reset_session_state

    get_settings.cache_clear()
    reset_session_state()

    config = _build_alembic_config(database_url)
    command.upgrade(config, "20260319_0007")

    engine = create_engine(database_url)
    base_time = datetime.now(tz=UTC)
    simulation_id = str(uuid4())
    realtime_session_id = str(uuid4())
    user_turn_id = str(uuid4())
    assistant_turn_id = str(uuid4())
    followup_user_turn_id = str(uuid4())

    try:
        with engine.begin() as connection:
            demo_user_id = connection.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": "demo@miro.local"},
            ).scalar_one()
            voice_profile_id = connection.execute(
                text(
                    """
                    SELECT id
                    FROM voice_profile_catalog
                    WHERE voice_profile_id = :voice_profile_id
                    """
                ),
                {"voice_profile_id": "vp_japan_female_01"},
            ).scalar_one()

            connection.execute(
                text(
                    """
                    INSERT INTO simulations (
                        id,
                        user_id,
                        country_key,
                        meeting_type_key,
                        goal_key,
                        duration_minutes,
                        voice_style_key,
                        voice_profile_catalog_id,
                        simulation_status,
                        setup_revision,
                        strategy_payload_json,
                        strategy_for_setup_revision,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :user_id,
                        :country_key,
                        :meeting_type_key,
                        :goal_key,
                        :duration_minutes,
                        :voice_style_key,
                        :voice_profile_catalog_id,
                        :simulation_status,
                        :setup_revision,
                        :strategy_payload_json,
                        :strategy_for_setup_revision,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                {
                    "id": simulation_id,
                    "user_id": demo_user_id,
                    "country_key": "Japan",
                    "meeting_type_key": "first_introduction",
                    "goal_key": "establish_trust_before_pricing",
                    "duration_minutes": 10,
                    "voice_style_key": "formal_measured",
                    "voice_profile_catalog_id": voice_profile_id,
                    "simulation_status": "strategy_ready",
                    "setup_revision": 1,
                    "strategy_payload_json": '{"templateKey":"seed"}',
                    "strategy_for_setup_revision": 1,
                    "created_at": base_time,
                    "updated_at": base_time,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO realtime_sessions (
                        id,
                        simulation_id,
                        user_id,
                        country_key,
                        meeting_type_key,
                        goal_key,
                        duration_minutes,
                        voice_style_key,
                        voice_profile_catalog_id,
                        setup_revision,
                        strategy_for_setup_revision,
                        transport,
                        session_status,
                        status_reason,
                        provider_mode,
                        provider_session_id,
                        provider_status,
                        provider_payload_json,
                        launch_payload_json,
                        launch_expires_at,
                        started_at,
                        ended_at,
                        created_at,
                        updated_at
                    ) VALUES (
                        :id,
                        :simulation_id,
                        :user_id,
                        :country_key,
                        :meeting_type_key,
                        :goal_key,
                        :duration_minutes,
                        :voice_style_key,
                        :voice_profile_catalog_id,
                        :setup_revision,
                        :strategy_for_setup_revision,
                        :transport,
                        :session_status,
                        :status_reason,
                        :provider_mode,
                        :provider_session_id,
                        :provider_status,
                        :provider_payload_json,
                        :launch_payload_json,
                        :launch_expires_at,
                        :started_at,
                        :ended_at,
                        :created_at,
                        :updated_at
                    )
                    """
                ),
                {
                    "id": realtime_session_id,
                    "simulation_id": simulation_id,
                    "user_id": demo_user_id,
                    "country_key": "Japan",
                    "meeting_type_key": "first_introduction",
                    "goal_key": "establish_trust_before_pricing",
                    "duration_minutes": 10,
                    "voice_style_key": "formal_measured",
                    "voice_profile_catalog_id": voice_profile_id,
                    "setup_revision": 1,
                    "strategy_for_setup_revision": 1,
                    "transport": "webrtc",
                    "session_status": "active",
                    "status_reason": None,
                    "provider_mode": "stub",
                    "provider_session_id": None,
                    "provider_status": "connected",
                    "provider_payload_json": '{"kind":"stub"}',
                    "launch_payload_json": (
                        '{"mode":"stub","transport":"webrtc","sessionToken":"seed-token",'
                        '"connectUrl":null,"fallbackTransport":"websocket",'
                        '"expiresAt":"2099-01-01T00:00:00Z"}'
                    ),
                    "launch_expires_at": base_time + timedelta(minutes=15),
                    "started_at": base_time,
                    "ended_at": None,
                    "created_at": base_time,
                    "updated_at": base_time,
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO realtime_session_turns (
                        id,
                        session_id,
                        turn_index,
                        parent_turn_id,
                        speaker,
                        input_mode,
                        source_text,
                        normalized_text,
                        language,
                        started_at,
                        ended_at,
                        created_at,
                        updated_at
                    ) VALUES
                    (
                        :user_turn_id,
                        :session_id,
                        1,
                        NULL,
                        'user',
                        'text',
                        'Need more alignment first.',
                        'Need more alignment first.',
                        'en',
                        NULL,
                        NULL,
                        :user_created_at,
                        :user_created_at
                    ),
                    (
                        :assistant_turn_id,
                        :session_id,
                        1,
                        :user_turn_id,
                        'assistant',
                        NULL,
                        'Let us align on the next step first.',
                        'Let us align on the next step first.',
                        'en',
                        NULL,
                        NULL,
                        :assistant_created_at,
                        :assistant_created_at
                    ),
                    (
                        :followup_user_turn_id,
                        :session_id,
                        1,
                        NULL,
                        'user',
                        'text',
                        'We should talk about price now.',
                        'We should talk about price now.',
                        'en',
                        NULL,
                        NULL,
                        :followup_created_at,
                        :followup_created_at
                    )
                    """
                ),
                {
                    "user_turn_id": user_turn_id,
                    "assistant_turn_id": assistant_turn_id,
                    "followup_user_turn_id": followup_user_turn_id,
                    "session_id": realtime_session_id,
                    "user_created_at": base_time + timedelta(seconds=1),
                    "assistant_created_at": base_time + timedelta(seconds=2),
                    "followup_created_at": base_time + timedelta(seconds=3),
                },
            )
            connection.execute(
                text(
                    """
                    INSERT INTO realtime_session_alerts (
                        id,
                        session_id,
                        turn_id,
                        severity,
                        issue_key,
                        title_text,
                        detail_text,
                        created_at,
                        updated_at
                    ) VALUES
                    (
                        :alert_one_id,
                        :session_id,
                        :user_turn_id,
                        'medium',
                        'underdeveloped_answer',
                        'Answer is too thin',
                        'The response is too short to move the conversation forward.',
                        :alert_one_created_at,
                        :alert_one_created_at
                    ),
                    (
                        :alert_two_id,
                        :session_id,
                        :followup_user_turn_id,
                        'high',
                        'premature_pricing_push',
                        'Price pressure is too early',
                        'This opening risks pushing pricing before trust is established.',
                        :alert_two_created_at,
                        :alert_two_created_at
                    )
                    """
                ),
                {
                    "alert_one_id": str(uuid4()),
                    "alert_two_id": str(uuid4()),
                    "session_id": realtime_session_id,
                    "user_turn_id": user_turn_id,
                    "followup_user_turn_id": followup_user_turn_id,
                    "alert_one_created_at": base_time + timedelta(seconds=4),
                    "alert_two_created_at": base_time + timedelta(seconds=5),
                },
            )

        command.upgrade(config, "head")
        reset_session_state()
        session_factory = get_session_factory()
        db_session = session_factory()
        try:
            record = db_session.scalar(
                select(RealtimeSession).where(RealtimeSession.id == realtime_session_id)
            )
            assert record is not None
            turns = db_session.scalars(
                select(RealtimeSessionTurn)
                .where(RealtimeSessionTurn.session_id == realtime_session_id)
                .order_by(RealtimeSessionTurn.turn_index.asc())
            ).all()
            assert [turn.turn_index for turn in turns] == [1, 2, 3]
            assert record.next_turn_index == 4
            assert record.turn_count == 3
            assert record.alert_count == 2
            assert record.last_alert_severity == "high"

            actor = CurrentActor(
                user_id=demo_user_id,
                email="demo@miro.local",
                organization_id=None,
            )
            exchange = realtime_service.respond_realtime_turn(
                db_session,
                actor,
                realtime_session_id,
                RealtimeTurnRespondRequest(
                    inputMode="text",
                    sourceText="We should align on one concrete next step before pricing.",
                    language="en",
                ),
            )
            assert exchange.userTurn.turnIndex == 4
            assert exchange.assistantTurn.turnIndex == 5
        finally:
            db_session.close()
    finally:
        engine.dispose()
        reset_session_state()
        get_settings.cache_clear()
