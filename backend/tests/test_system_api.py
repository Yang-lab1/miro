def test_readiness_is_available_for_local_development(client):
    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["reachable"] is True
    assert payload["checks"]["llm"]["configured"] is True
    assert payload["checks"]["hardware"]["configured"] is False


def test_production_readiness_rejects_missing_provider_configuration(make_client):
    client = make_client(
        APP_ENV="production",
        LLM_PROVIDER_MODE="openai_compatible",
        LLM_API_KEY="",
        DOUBAO_API_KEY="",
        DOUBAO_APP_ID="",
        DOUBAO_ACCESS_TOKEN="",
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["checks"]["database"]["reachable"] is True
    assert payload["checks"]["llm"]["configured"] is False
    assert payload["checks"]["doubao"]["configured"] is False
    assert payload["checks"]["hardware"]["configured"] is False


def test_production_readiness_rejects_rule_based_text_generation(make_client):
    client = make_client(
        APP_ENV="production",
        LLM_PROVIDER_MODE="rule_based",
        HARDWARE_PROVIDER_MODE="bluetooth",
        BROWSER_VOICE_FALLBACK_ENABLED="true",
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["checks"]["llm"]["configured"] is False
    assert payload["checks"]["hardware"]["configured"] is True
