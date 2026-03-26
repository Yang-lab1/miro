import pytest


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
