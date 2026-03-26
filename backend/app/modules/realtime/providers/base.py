from dataclasses import dataclass
from typing import Protocol

from app.api.schemas.realtime import RealtimeLaunchResponse, RealtimeTransport


@dataclass(slots=True)
class RealtimeLaunchContext:
    actor_user_id: str
    simulation_id: str
    transport: RealtimeTransport


@dataclass(slots=True)
class RealtimeProviderLaunchResult:
    launch: RealtimeLaunchResponse
    provider_mode: str
    provider_session_id: str | None
    provider_status: str
    provider_payload_json: dict | None


@dataclass(slots=True)
class RealtimeProviderSyncContext:
    session_id: str
    transport: RealtimeTransport
    provider_mode: str | None
    provider_session_id: str | None
    provider_status: str | None
    provider_payload_json: dict | None


@dataclass(slots=True)
class RealtimeProviderSyncResult:
    provider_status: str | None
    provider_payload_json: dict | None


@dataclass(slots=True)
class RealtimeGroundingFileContext:
    file_id: str
    file_name: str
    content_type: str
    size_bytes: int
    source_type: str | None
    storage_key: str | None
    parse_status: str | None
    upload_status: str


@dataclass(slots=True)
class RealtimeGroundingContext:
    simulation_id: str
    country_key: str
    meeting_type_key: str
    goal_key: str
    duration_minutes: int
    voice_style_key: str
    setup_revision: int
    strategy_for_setup_revision: int | None
    strategy_summary_en: str | None
    strategy_bullets_en: list[str]
    uploaded_files: list[RealtimeGroundingFileContext]


@dataclass(slots=True)
class RealtimeTurnGenerationContext:
    session_id: str
    provider_mode: str | None
    language: str
    normalized_text: str
    grounding: RealtimeGroundingContext


@dataclass(slots=True)
class RealtimeTurnGenerationResult:
    assistant_text: str
    focus_phrase: str


@dataclass(slots=True)
class RealtimeAlertSpec:
    severity: str
    issue_key: str
    title_text: str
    detail_text: str | None


@dataclass(slots=True)
class RealtimeAlertExtractionContext:
    session_id: str
    normalized_text: str
    grounding: RealtimeGroundingContext


class RealtimeProvider(Protocol):
    mode: str

    def create_launch(
        self,
        context: RealtimeLaunchContext,
    ) -> RealtimeProviderLaunchResult:
        ...

    def sync_runtime_state(
        self,
        context: RealtimeProviderSyncContext,
    ) -> RealtimeProviderSyncResult:
        ...
