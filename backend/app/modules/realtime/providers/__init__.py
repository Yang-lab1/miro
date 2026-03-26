from app.core.config import get_settings
from app.core.errors import AppError
from app.modules.realtime.providers.base import RealtimeProvider
from app.modules.realtime.providers.mock_remote import MockRemoteRealtimeProvider
from app.modules.realtime.providers.stub import StubRealtimeProvider


def get_realtime_provider(mode: str | None = None) -> RealtimeProvider:
    provider_mode = mode or get_settings().realtime_provider_mode

    if provider_mode == "stub":
        return StubRealtimeProvider()
    if provider_mode == "mock_remote":
        return MockRemoteRealtimeProvider()

    raise AppError(
        status_code=500,
        code="realtime_provider_unavailable",
        message="Realtime provider mode is not supported.",
        details={"mode": provider_mode},
    )
