from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine

    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
        )

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory

    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    return _session_factory


def get_db() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def ping_database() -> bool:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
    return True


def reset_session_state() -> None:
    global _engine, _session_factory

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _session_factory = None
