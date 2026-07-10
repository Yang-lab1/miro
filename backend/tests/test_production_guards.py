def _build_ready_simulation(client, headers):
    simulation = client.post(
        "/api/v1/simulations",
        json={
            "countryKey": "Japan",
            "meetingType": "first_introduction",
            "goal": "establish_trust_before_pricing",
            "durationMinutes": 10,
            "voiceStyle": "formal_measured",
            "voiceProfileId": "vp_japan_female_01",
            "constraints": "Keep the conversation calm and structured.",
        },
        headers=headers,
    )
    assert simulation.status_code == 200
    simulation_id = simulation.json()["simulationId"]

    strategy = client.post(
        f"/api/v1/simulations/{simulation_id}/strategy",
        headers=headers,
    )
    assert strategy.status_code == 200

    realtime = client.post(
        "/api/v1/realtime/sessions",
        json={"simulationId": simulation_id, "skipLearningPrecheck": True},
        headers=headers,
    )
    assert realtime.status_code == 200
    session_id = realtime.json()["sessionId"]

    started = client.post(
        f"/api/v1/realtime/sessions/{session_id}/start",
        headers=headers,
    )
    assert started.status_code == 200
    return session_id


def test_production_rejects_synthetic_speech_input(
    make_client,
    supabase_jwks_server,
    monkeypatch,
):
    from app.modules.realtime import service as realtime_service
    from app.modules.realtime.turn_engine import RuleBasedRealtimeTurnGenerator

    monkeypatch.setattr(
        realtime_service,
        "get_turn_generator",
        lambda: RuleBasedRealtimeTurnGenerator(),
    )
    client = make_client(
        APP_ENV="production",
        LLM_PROVIDER_MODE="openai_compatible",
        LLM_API_KEY="test-key",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    user_id = "production-guard-speech-user"
    token = supabase_jwks_server["issue_token"](sub=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    session_id = _build_ready_simulation(client, headers)

    response = client.post(
        f"/api/v1/realtime/sessions/{session_id}/turns/respond",
        json={"inputMode": "speech_stub", "sourceText": "A synthetic answer."},
        headers=headers,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "realtime_speech_provider_required"


def test_production_rejects_demo_hardware_sync(make_client, supabase_jwks_server):
    client = make_client(
        APP_ENV="production",
        HARDWARE_PROVIDER_MODE="demo",
        SUPABASE_URL=supabase_jwks_server["base_url"],
    )
    token = supabase_jwks_server["issue_token"](sub="production-guard-hardware-user")
    headers = {"Authorization": f"Bearer {token}"}
    devices = client.get("/api/v1/hardware/devices", headers=headers)
    assert devices.status_code == 200
    device_id = devices.json()[0]["deviceId"]

    response = client.post(
        f"/api/v1/hardware/devices/{device_id}/sync",
        json={
            "syncKind": "download",
            "healthStatus": "healthy",
            "summaryText": "Review report",
        },
        headers=headers,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "hardware_provider_not_configured"
