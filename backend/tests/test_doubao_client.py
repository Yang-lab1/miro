from app.modules.realtime.doubao_client import DoubaoCredentials


def test_doubao_credentials_support_new_api_key_headers():
    credentials = DoubaoCredentials(
        app_id="legacy-app",
        api_key="new-api-key",
        access_token="legacy-token",
        resource_id="volc.speech.dialog",
        app_key="legacy-key",
    )

    headers = credentials.headers(connect_id="connect-1")

    assert headers["X-Api-Key"] == "new-api-key"
    assert headers["X-Api-Resource-Id"] == "volc.speech.dialog"
    assert headers["X-Api-Connect-Id"] == "connect-1"
    assert "X-Api-App-ID" not in headers


def test_doubao_credentials_keep_legacy_headers_when_api_key_is_empty():
    credentials = DoubaoCredentials(
        app_id="legacy-app",
        access_token="legacy-token",
        resource_id="volc.speech.dialog",
        app_key="legacy-key",
    )

    headers = credentials.headers()

    assert headers["X-Api-App-ID"] == "legacy-app"
    assert headers["X-Api-Access-Key"] == "legacy-token"
    assert headers["X-Api-App-Key"] == "legacy-key"
    assert "X-Api-Key" not in headers
