import json
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "miro-backend"
    app_env: str = "development"
    app_debug: bool = False
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
    frontend_site_url: str | None = None
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/miro"
    database_echo: bool = False
    enable_docs: bool = True
    supabase_url: str | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: str | None = None
    allow_demo_actor_fallback: bool = False
    demo_user_email: str = "demo@miro.local"
    realtime_provider_mode: str = "stub"

    # --- Doubao / Volcengine Realtime Dialogue ---
    doubao_app_id: str = ""
    doubao_access_token: str = ""
    doubao_secret_key: str = ""
    doubao_resource_id: str = "volc.speech.dialog"
    doubao_app_key: str = "PlgvMymc7f3tQnJ6"
    doubao_speaker: str = "zh_female_vv_jupiter_bigtts"
    doubao_model: str = "1.2.1.1"
    doubao_ws_url: str = "wss://openspeech.bytedance.com/api/v3/realtime/dialogue"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value: object) -> object:
        if value is None:
            return []

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []

            if stripped.startswith("["):
                parsed = json.loads(stripped)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ORIGINS JSON value must be a list.")
                return [item.strip() for item in parsed if isinstance(item, str) and item.strip()]

            return [item.strip() for item in stripped.split(",") if item.strip()]

        return value

    @property
    def resolved_frontend_origin(self) -> str | None:
        if not self.frontend_site_url:
            return None

        parsed = urlsplit(self.frontend_site_url.strip())
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def resolved_cors_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins if origin and origin.strip()]
        frontend_origin = self.resolved_frontend_origin
        if frontend_origin:
            origins.append(frontend_origin)

        unique_origins: list[str] = []
        for origin in origins:
            if origin not in unique_origins:
                unique_origins.append(origin)
        return unique_origins

    @property
    def resolved_supabase_jwt_issuer(self) -> str | None:
        if self.supabase_jwt_issuer:
            return self.supabase_jwt_issuer.rstrip("/")
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1"
        return None

    @property
    def resolved_supabase_jwks_url(self) -> str | None:
        if self.supabase_jwks_url:
            return self.supabase_jwks_url.rstrip("/")
        if self.supabase_url:
            return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
