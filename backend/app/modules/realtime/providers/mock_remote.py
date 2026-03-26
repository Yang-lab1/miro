import secrets
from datetime import UTC, datetime, timedelta

from app.api.schemas.realtime import RealtimeLaunchResponse
from app.modules.realtime.providers.base import (
    RealtimeLaunchContext,
    RealtimeProviderLaunchResult,
    RealtimeProviderSyncContext,
    RealtimeProviderSyncResult,
)


class MockRemoteRealtimeProvider:
    mode = "mock_remote"

    def create_launch(
        self,
        context: RealtimeLaunchContext,
    ) -> RealtimeProviderLaunchResult:
        provider_session_id = f"mock_{secrets.token_urlsafe(12)}"
        expires_at = datetime.now(tz=UTC) + timedelta(minutes=15)
        fallback_transport = "websocket" if context.transport == "webrtc" else None
        connect_url = f"https://mock-provider.local/session/{provider_session_id}"
        launch = RealtimeLaunchResponse(
            mode=self.mode,
            transport=context.transport,
            sessionToken=secrets.token_urlsafe(24),
            connectUrl=connect_url,
            fallbackTransport=fallback_transport,
            expiresAt=expires_at,
        )
        return RealtimeProviderLaunchResult(
            launch=launch,
            provider_mode=self.mode,
            provider_session_id=provider_session_id,
            provider_status="created",
            provider_payload_json={
                "kind": "mock_remote",
                "providerSessionId": provider_session_id,
                "connectUrl": connect_url,
                "simulatedProviderStatus": "created",
            },
        )

    def sync_runtime_state(
        self,
        context: RealtimeProviderSyncContext,
    ) -> RealtimeProviderSyncResult:
        payload = dict(context.provider_payload_json or {})
        simulated_status = payload.get("simulatedProviderStatus")
        provider_status = context.provider_status

        if isinstance(simulated_status, str):
            provider_status = simulated_status

        return RealtimeProviderSyncResult(
            provider_status=provider_status,
            provider_payload_json=payload,
        )
