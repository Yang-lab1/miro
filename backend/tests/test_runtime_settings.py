from app.core.config import Settings


def test_settings_parse_comma_separated_cors_origins_and_frontend_origin():
    settings = Settings(
        cors_origins="https://app.example.com, https://preview.example.com",
        frontend_site_url="https://miro.example.com/pricing?view=plans",
    )

    assert settings.resolved_frontend_origin == "https://miro.example.com"
    assert settings.resolved_cors_origins == [
        "https://app.example.com",
        "https://preview.example.com",
        "https://miro.example.com",
    ]


def test_settings_parse_json_cors_origins():
    settings = Settings(
        cors_origins='["https://app.example.com","https://preview.example.com"]'
    )

    assert settings.resolved_cors_origins == [
        "https://app.example.com",
        "https://preview.example.com",
    ]


def test_settings_derive_supabase_auth_urls_from_project_url():
    settings = Settings(supabase_url="https://demo-project.supabase.co")

    assert (
        settings.resolved_supabase_jwt_issuer
        == "https://demo-project.supabase.co/auth/v1"
    )
    assert (
        settings.resolved_supabase_jwks_url
        == "https://demo-project.supabase.co/auth/v1/.well-known/jwks.json"
    )
