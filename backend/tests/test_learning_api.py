import pytest

from app.models.learning import UserLearningModuleState
from app.models.user import User


def test_learning_countries_returns_multilingual_payload(client):
    response = client.get("/api/v1/learning/countries")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert payload[0]["countryName"] == {"en": "Germany", "zh": "德国"}
    assert payload[1]["countryKey"] == "Japan"
    assert payload[1]["latestContentVersion"] == "2026.03"


def test_learning_country_detail_and_unknown_country(client):
    response = client.get("/api/v1/learning/countries/Japan")

    assert response.status_code == 200
    payload = response.json()
    assert payload["countryKey"] == "Japan"
    assert payload["countryName"] == {"en": "Japan", "zh": "日本"}
    assert payload["defaultMeetingType"] == "first_introduction"
    assert len(payload["sections"]) >= 1

    missing = client.get("/api/v1/learning/countries/Unknown")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "country_not_found"


@pytest.mark.parametrize(
    ("country_key", "expected_status", "expected_up_to_date"),
    [
        ("Japan", "completed", True),
        ("Germany", "completed", False),
        ("UAE", "missing", False),
    ],
)
def test_learning_progress_states(client, country_key, expected_status, expected_up_to_date):
    response = client.get(f"/api/v1/learning/progress/{country_key}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["countryKey"] == country_key
    assert payload["status"] == expected_status
    assert payload["isUpToDate"] is expected_up_to_date


def test_complete_learning_progress_and_invalid_version(client):
    invalid = client.post(
        "/api/v1/learning/progress/UAE/complete",
        json={"contentVersion": "2026.02"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_content_version"

    complete = client.post(
        "/api/v1/learning/progress/UAE/complete",
        json={"contentVersion": "2026.03"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"
    assert complete.json()["isUpToDate"] is True


@pytest.mark.parametrize(
    ("country_key", "expected_reason", "expected_ready"),
    [
        ("Japan", "ready", True),
        ("Germany", "learning_outdated", False),
        ("UAE", "learning_required", False),
        ("Unknown", "country_not_supported", False),
    ],
)
def test_simulation_precheck_branches(client, country_key, expected_reason, expected_ready):
    response = client.post("/api/v1/simulations/precheck", json={"countryKey": country_key})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reason"] == expected_reason
    assert payload["ready"] is expected_ready


def test_voice_profiles_returns_public_identifiers_and_unknown_country(client):
    response = client.get("/api/v1/voice-profiles", params={"countryKey": "Japan"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["voiceProfileId"] == "vp_japan_female_01"
    assert payload[0]["providerVoiceId"] == "ja_female_01"

    missing = client.get("/api/v1/voice-profiles", params={"countryKey": "Unknown"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "country_not_found"


def test_learning_modules_returns_board_shape(client):
    response = client.get("/api/v1/learning/modules")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"recommendedModule", "snapshotCounts", "items"}
    assert set(payload["snapshotCounts"]) == {"open", "new", "saved"}
    assert payload["recommendedModule"] is not None
    assert payload["items"]

    first_item = payload["items"][0]
    assert set(first_item) == {
        "moduleId",
        "countryKey",
        "title",
        "summary",
        "theme",
        "scene",
        "status",
        "stateLabel",
        "saved",
        "recommended",
        "sortOrder",
    }


def test_learning_modules_support_filters_and_empty_result(client):
    board = client.get("/api/v1/learning/modules")
    assert board.status_code == 200
    payload = board.json()
    japan_module = next(item for item in payload["items"] if item["countryKey"] == "Japan")
    germany_module = next(item for item in payload["items"] if item["countryKey"] == "Germany")

    saved = client.post(
        f"/api/v1/learning/modules/{germany_module['moduleId']}/state",
        json={"action": "save"},
    )
    started = client.post(
        f"/api/v1/learning/modules/{japan_module['moduleId']}/state",
        json={"action": "start"},
    )
    assert saved.status_code == 200
    assert started.status_code == 200

    filtered = client.get(
        "/api/v1/learning/modules",
        params={
            "countryKey": "Germany",
            "theme": germany_module["theme"],
            "scene": germany_module["scene"],
            "status": "saved",
            "tab": "saved",
            "query": germany_module["title"].split()[0],
        },
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert len(filtered_payload["items"]) == 1
    assert filtered_payload["items"][0]["moduleId"] == germany_module["moduleId"]
    assert filtered_payload["items"][0]["status"] == "saved"

    empty = client.get(
        "/api/v1/learning/modules",
        params={"countryKey": "Japan", "theme": "nonexistent"},
    )
    assert empty.status_code == 200
    empty_payload = empty.json()
    assert empty_payload["recommendedModule"] is None
    assert empty_payload["items"] == []
    assert empty_payload["snapshotCounts"] == {"open": 1, "new": 4, "saved": 1}


def test_learning_module_state_actions_update_actor_state(client):
    board = client.get("/api/v1/learning/modules")
    assert board.status_code == 200
    module_id = board.json()["items"][0]["moduleId"]

    started = client.post(
        f"/api/v1/learning/modules/{module_id}/state",
        json={"action": "start"},
    )
    assert started.status_code == 200
    start_payload = started.json()
    assert start_payload["item"]["moduleId"] == module_id
    assert start_payload["item"]["status"] == "open"
    assert start_payload["snapshotCounts"]["open"] == 1

    saved = client.post(
        f"/api/v1/learning/modules/{module_id}/state",
        json={"action": "save"},
    )
    assert saved.status_code == 200
    assert saved.json()["item"]["saved"] is True

    completed = client.post(
        f"/api/v1/learning/modules/{module_id}/state",
        json={"action": "complete"},
    )
    assert completed.status_code == 200
    assert completed.json()["item"]["status"] == "completed"

    unsaved = client.post(
        f"/api/v1/learning/modules/{module_id}/state",
        json={"action": "unsave"},
    )
    assert unsaved.status_code == 200
    assert unsaved.json()["item"]["saved"] is False


def test_learning_module_state_is_actor_scoped(client, db_session):
    board = client.get("/api/v1/learning/modules")
    assert board.status_code == 200
    module = board.json()["items"][0]

    other_user = User(email="other-learning@miro.local", status="active")
    db_session.add(other_user)
    db_session.flush()
    db_session.add(
        UserLearningModuleState(
            user_id=other_user.id,
            module_id=module["moduleId"],
        )
    )
    db_session.commit()

    response = client.get("/api/v1/learning/modules", params={"countryKey": module["countryKey"]})

    assert response.status_code == 200
    payload = response.json()
    current_module = next(
        item for item in payload["items"] if item["moduleId"] == module["moduleId"]
    )
    assert current_module["status"] == "new"
    assert current_module["saved"] is False

    updated = client.post(
        f"/api/v1/learning/modules/{module['moduleId']}/state",
        json={"action": "save"},
    )
    assert updated.status_code == 200

    db_session.expire_all()
    other_state = db_session.query(UserLearningModuleState).filter_by(user_id=other_user.id).one()
    assert other_state.saved_at is None
    assert other_state.started_at is None
    assert other_state.completed_at is None


def test_learning_module_state_returns_404_for_missing_module(client):
    response = client.post(
        "/api/v1/learning/modules/module_missing/state",
        json={"action": "save"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "learning_module_not_found"
