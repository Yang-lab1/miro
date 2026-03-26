import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from uuid import uuid4

import jwt
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

BACKEND_DIR = Path(__file__).resolve().parents[1]


class _JWKSRequestHandler(BaseHTTPRequestHandler):
    jwks_payload = b"{}"

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/auth/v1/.well-known/jwks.json":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(self.jwks_payload)))
        self.end_headers()
        self.wfile.write(self.jwks_payload)

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


@pytest.fixture()
def configured_database(tmp_path, monkeypatch):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ALLOW_DEMO_ACTOR_FALLBACK", "true")
    monkeypatch.setenv("DEMO_USER_EMAIL", "demo@miro.local")

    from app.core.config import get_settings
    from app.db.session import reset_session_state

    get_settings.cache_clear()
    reset_session_state()

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")

    yield database_url

    reset_session_state()
    get_settings.cache_clear()


@pytest.fixture()
def app(configured_database):
    from app.main import create_application

    return create_application()


@pytest.fixture()
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(configured_database):
    from app.db.session import get_session_factory

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_client(configured_database, monkeypatch):
    clients: list[TestClient] = []

    def _make_client(**env_overrides: str | None) -> TestClient:
        from app.core.config import get_settings

        for key, value in env_overrides.items():
            if value is None:
                monkeypatch.delenv(key, raising=False)
            else:
                monkeypatch.setenv(key, value)

        get_settings.cache_clear()

        from app.main import create_application

        client = TestClient(create_application())
        client.__enter__()
        clients.append(client)
        return client

    yield _make_client

    while clients:
        client = clients.pop()
        client.__exit__(None, None, None)

    from app.core.config import get_settings

    get_settings.cache_clear()


@pytest.fixture()
def supabase_jwks_server():
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk.update({"kid": "test-signing-key", "alg": "RS256", "use": "sig"})

    handler = type(
        "JWKSHandler",
        (_JWKSRequestHandler,),
        {"jwks_payload": json.dumps({"keys": [jwk]}).encode("utf-8")},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{server.server_port}"
    issuer = f"{base_url}/auth/v1"

    def issue_token(
        *,
        sub: str | None = None,
        email: str | None = "user@miro.local",
        role: str = "authenticated",
        audience: str = "authenticated",
        issuer_override: str | None = None,
        expires_in_seconds: int = 3600,
        is_anonymous: bool | None = None,
        private_key_override=None,
        extra_claims: dict | None = None,
    ) -> str:
        claims = {
            "iss": issuer_override or issuer,
            "aud": audience,
            "exp": int(time.time()) + expires_in_seconds,
            "sub": sub or str(uuid4()),
            "role": role,
            "email": email,
        }
        if is_anonymous is not None:
            claims["is_anonymous"] = is_anonymous
        if extra_claims:
            claims.update(extra_claims)

        return jwt.encode(
            claims,
            private_key_override or private_key,
            algorithm="RS256",
            headers={"kid": "test-signing-key"},
        )

    yield {
        "base_url": base_url,
        "issuer": issuer,
        "issue_token": issue_token,
    }

    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
