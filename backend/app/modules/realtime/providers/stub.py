import secrets
from datetime import UTC, datetime, timedelta

from app.api.schemas.realtime import RealtimeLaunchResponse
from app.modules.realtime.providers.base import (
    RealtimeLaunchContext,
    RealtimeProviderLaunchResult,
    RealtimeProviderSyncContext,
    RealtimeProviderSyncResult,
)


class StubRealtimeProvider:
    mode = "stub"

    def create_launch(
        self,
        context: RealtimeLaunchContext,
    ) -> RealtimeProviderLaunchResult:
        expires_at = datetime.now(tz=UTC) + timedelta(minutes=15)
        fallback_transport = "websocket" if context.transport == "webrtc" else None
        launch = RealtimeLaunchResponse(
            mode=self.mode,
            transport=context.transport,
            sessionToken=secrets.token_urlsafe(24),
            connectUrl=None,
            fallbackTransport=fallback_transport,
            expiresAt=expires_at,
        )
        return RealtimeProviderLaunchResult(
            launch=launch,
            provider_mode=self.mode,
            provider_session_id=None,
            provider_status="created",
            provider_payload_json={"kind": "stub"},
        )

    def sync_runtime_state(
        self,
        context: RealtimeProviderSyncContext,
    ) -> RealtimeProviderSyncResult:
        return RealtimeProviderSyncResult(
            provider_status=context.provider_status,
            provider_payload_json=context.provider_payload_json,
        )
