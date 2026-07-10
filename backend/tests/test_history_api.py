from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from app.models.hardware import Device, DeviceSyncEvent
from app.models.review import Review
from app.models.simulation import (
    RealtimeSession,
    Simulation,
    SimulationUploadedFile,
    VoiceProfileCatalog,
)
from app.models.user import User
from app.services.current_actor import resolve_current_actor


def _seed_user(db_session, *, email: str) -> User:
    user = User(email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def _get_voice_profile(db_session, voice_profile_id: str) -> VoiceProfileCatalog:
    voice_profile = db_session.scalar(
        select(VoiceProfileCatalog).where(VoiceProfileCatalog.voice_profile_id == voice_profile_id)
    )
    assert voice_profile is not None
    return voice_profile


def _seed_source_simulation_bundle(
    db_session,
    *,
    user_id: str,
    country_key: str = "Japan",
    review_source: str = "realtime_session",
    with_uploaded_file: bool = True,
    with_complete_setup: bool = True,
) -> tuple[Simulation, RealtimeSession | None, Review]:
    voice_profile = _get_voice_profile(db_session, "vp_japan_female_01")
    simulation = Simulation(
        user_id=user_id,
        country_key=country_key,
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id=voice_profile.id,
        constraints_text="Keep the exchange measured.",
        simulation_status="strategy_ready",
        setup_revision=2,
        strategy_payload_json={"templateKey": "seed"},
        strategy_for_setup_revision=2,
    )
    db_session.add(simulation)
    db_session.flush()

    if with_uploaded_file:
        db_session.add(
            SimulationUploadedFile(
                simulation_id=simulation.id,
                file_name="renewal-notes.txt",
                content_type="text/plain",
                size_bytes=128,
                upload_status="registered",
                storage_key=None,
                parse_status="ready",
                source_type="manual_upload",
                extracted_summary_text="Renewal timing should stay conservative.",
                extracted_excerpt_text="Confirm the internal owner before pricing.",
            )
        )

    realtime_session = None
    if review_source == "realtime_session":
        realtime_session = RealtimeSession(
            simulation_id=simulation.id,
            user_id=user_id,
            country_key=country_key,
            meeting_type_key="first_introduction",
            goal_key="establish_trust_before_pricing",
            duration_minutes=10,
            voice_style_key="formal_measured",
            voice_profile_catalog_id=voice_profile.id,
            setup_revision=2,
            strategy_for_setup_revision=2,
            transport="webrtc",
            session_status="ended",
            provider_mode="stub",
            provider_status="closed",
            provider_payload_json={"kind": "stub"},
            launch_payload_json={"kind": "stub"},
            turn_count=2,
            alert_count=1,
            started_at=datetime.now(tz=UTC) - timedelta(minutes=10),
            ended_at=datetime.now(tz=UTC) - timedelta(minutes=5),
        )
        db_session.add(realtime_session)
        db_session.flush()

    review = Review(
        user_id=user_id,
        realtime_session_id=realtime_session.id if realtime_session else None,
        review_source=review_source,
        country_key=country_key,
        meeting_type_key="first_introduction" if with_complete_setup else None,
        goal_key="establish_trust_before_pricing" if with_complete_setup else None,
        duration_minutes=10 if with_complete_setup else None,
        voice_style_key="formal_measured" if with_complete_setup else None,
        voice_profile_catalog_id=voice_profile.id if with_complete_setup else None,
        setup_revision=2 if with_complete_setup else None,
        strategy_for_setup_revision=2 if with_complete_setup else None,
        review_status="ready",
        overall_assessment="mixed",
        title_text="Good momentum with room to sharpen.",
        score_total=68,
        summary_json={
            "headline": "Good momentum with room to sharpen.",
            "coachSummary": "Uploaded brief stayed relevant and the pacing improved.",
            "nextStep": "Hold pricing until trust is visible.",
        },
        metrics_json={
            "turnCount": 4,
            "alertCount": 1,
            "highSeverityCount": 0,
            "mediumSeverityCount": 1,
            "topIssueKeys": ["premature_pricing_push"],
        },
        repeated_issues_json=["premature_pricing_push"],
        ended_at=datetime.now(tz=UTC) - timedelta(minutes=5),
    )
    db_session.add(review)
    db_session.commit()
    return simulation, realtime_session, review


def _seed_device_sync_event(
    db_session,
    *,
    user_id: str,
    review_id: str | None,
    created_at: datetime,
    health_status: str = "warning",
    summary_text: str = "Demo upload completed",
    detail_text: str = "18 language events uploaded.",
) -> DeviceSyncEvent:
    device = Device(
        user_id=user_id,
        device_name="Miro Pin 01",
        firmware_version="1.4.2",
        connection_state="connected",
        transfer_state="healthy",
        battery_percent=80,
    )
    db_session.add(device)
    db_session.flush()

    event = DeviceSyncEvent(
        device_id=device.id,
        review_id=review_id,
        health_status=health_status,
        summary_text=summary_text,
        payload_json={"syncKind": "upload", "detailText": detail_text},
    )
    event.created_at = created_at
    event.updated_at = created_at
    db_session.add(event)
    db_session.commit()
    return event


def test_history_records_returns_unified_actor_scoped_feed(client, db_session):
    actor = resolve_current_actor(db_session)
    _, realtime_session, review = _seed_source_simulation_bundle(db_session, user_id=actor.user_id)
    sync_event = _seed_device_sync_event(
        db_session,
        user_id=actor.user_id,
        review_id=review.id,
        created_at=datetime.now(tz=UTC),
    )

    response = client.get("/api/v1/history/records")

    assert response.status_code == 200
    payload = response.json()
    assert [item["recordType"] for item in payload["items"]][:2] == ["hardware_sync", "review"]
    review_item = next(item for item in payload["items"] if item["recordType"] == "review")
    sync_item = next(item for item in payload["items"] if item["recordType"] == "hardware_sync")
    assert review_item["reviewId"] == review.id
    assert review_item["sourceSessionId"] == realtime_session.id
    assert review_item["canContinue"] is True
    assert review_item["canOpenReview"] is True
    assert review_item["canReplay"] is True
    assert review_item["score"] == 68
    assert sync_item["recordId"] == sync_event.id
    assert sync_item["reviewId"] == review.id
    assert sync_item["countryKey"] == "Japan"
    assert sync_item["status"] == "warning"
    assert sync_item["canOpenReview"] is True


def test_history_records_support_filters_and_empty_state(client, db_session):
    actor = resolve_current_actor(db_session)
    _seed_source_simulation_bundle(db_session, user_id=actor.user_id, country_key="Japan")
    _seed_source_simulation_bundle(db_session, user_id=actor.user_id, country_key="Germany")

    review_only = client.get(
        "/api/v1/history/records",
        params={"type": "review", "countryKey": "Japan"},
    )
    assert review_only.status_code == 200
    assert len(review_only.json()["items"]) == 1
    assert review_only.json()["items"][0]["countryKey"] == "Japan"

    empty = client.get("/api/v1/history/records", params={"query": "not-found-anywhere"})
    assert empty.status_code == 200
    assert empty.json() == {"items": []}


def test_history_records_are_actor_scoped(client, db_session):
    actor = resolve_current_actor(db_session)
    _, _, own_review = _seed_source_simulation_bundle(db_session, user_id=actor.user_id)
    other_user = _seed_user(db_session, email=f"other-{uuid4()}@miro.local")
    _, _, other_review = _seed_source_simulation_bundle(db_session, user_id=other_user.id)
    _seed_device_sync_event(
        db_session,
        user_id=other_user.id,
        review_id=other_review.id,
        created_at=datetime.now(tz=UTC),
    )

    response = client.get("/api/v1/history/records")

    assert response.status_code == 200
    record_ids = {item["recordId"] for item in response.json()["items"]}
    assert own_review.id in record_ids
    assert other_review.id not in record_ids


def test_continue_from_review_creates_new_simulation_and_copies_uploaded_context(
    client,
    db_session,
):
    actor = resolve_current_actor(db_session)
    source_simulation, realtime_session, review = _seed_source_simulation_bundle(
        db_session,
        user_id=actor.user_id,
        with_uploaded_file=True,
    )

    response = client.post(f"/api/v1/simulations/from-review/{review.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["simulationId"] != source_simulation.id
    assert payload["countryKey"] == review.country_key
    assert payload["meetingType"] == review.meeting_type_key
    assert payload["goal"] == review.goal_key
    assert payload["durationMinutes"] == review.duration_minutes
    assert payload["voiceStyle"] == review.voice_style_key
    assert payload["voiceProfileId"] == "vp_japan_female_01"
    assert payload["status"] == "ready_for_strategy"
    assert payload["strategy"] is None
    assert len(payload["uploadedFiles"]) == 1

    new_simulation = db_session.scalar(
        select(Simulation).where(Simulation.id == payload["simulationId"])
    )
    assert new_simulation is not None
    assert new_simulation.constraints_text == source_simulation.constraints_text

    cloned_files = db_session.scalars(
        select(SimulationUploadedFile).where(
            SimulationUploadedFile.simulation_id == new_simulation.id
        )
    ).all()
    assert len(cloned_files) == 1
    assert cloned_files[0].id != db_session.scalar(
        select(SimulationUploadedFile.id).where(
            SimulationUploadedFile.simulation_id == source_simulation.id
        )
    )
    assert cloned_files[0].extracted_summary_text == "Renewal timing should stay conservative."
    assert cloned_files[0].extracted_excerpt_text == "Confirm the internal owner before pricing."

    original_review = db_session.scalar(select(Review).where(Review.id == review.id))
    original_realtime = db_session.scalar(
        select(RealtimeSession).where(RealtimeSession.id == realtime_session.id)
    )
    original_source_simulation = db_session.scalar(
        select(Simulation).where(Simulation.id == source_simulation.id)
    )
    assert original_review is not None
    assert original_realtime is not None
    assert original_source_simulation is not None
    assert original_review.realtime_session_id == realtime_session.id
    assert original_source_simulation.id == source_simulation.id


def test_continue_from_review_returns_404_for_missing_or_foreign_review(client, db_session):
    actor = resolve_current_actor(db_session)
    other_user = _seed_user(db_session, email=f"foreign-{uuid4()}@miro.local")
    _, _, other_review = _seed_source_simulation_bundle(db_session, user_id=other_user.id)
    _seed_source_simulation_bundle(db_session, user_id=actor.user_id)

    missing = client.post(f"/api/v1/simulations/from-review/{uuid4()}")
    foreign = client.post(f"/api/v1/simulations/from-review/{other_review.id}")

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "review_not_found"
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "review_not_found"


def test_continue_from_review_rejects_review_without_complete_setup(client, db_session):
    actor = resolve_current_actor(db_session)
    _, _, review = _seed_source_simulation_bundle(
        db_session,
        user_id=actor.user_id,
        review_source="device",
        with_complete_setup=False,
    )

    response = client.post(f"/api/v1/simulations/from-review/{review.id}")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "review_continue_not_ready"
