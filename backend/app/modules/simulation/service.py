from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.common import LocalizedText
from app.api.schemas.simulation import (
    SimulationCreateRequest,
    SimulationFilesRequest,
    SimulationPatchRequest,
    SimulationPrecheckLearningState,
    SimulationPrecheckResponse,
    SimulationResponse,
    SimulationSetupDefaultsResponse,
    SimulationStrategyBullets,
    SimulationStrategyGeneratedFrom,
    SimulationStrategyItem,
    SimulationStrategyOutlineQuestion,
    SimulationStrategyResponse,
    SimulationUploadedFileResponse,
)
from app.api.schemas.voice_profiles import VoiceProfileResponseItem
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.shared_catalog import load_enum_keys
from app.models.review import Review
from app.models.simulation import (
    RealtimeSession,
    Simulation,
    SimulationUploadedFile,
    VoiceProfileCatalog,
)
from app.models.user import UserTwinMemory
from app.modules.learning import service as learning_service
from app.modules.simulation.continuation import (
    ReviewContinuationSource,
    UploadedContextCloneSource,
    build_continued_simulation_seed,
    review_can_continue,
)
from app.modules.simulation.file_extraction import extract_uploaded_file_content
from app.modules.simulation.strategy_generation import (
    OpenAICompatibleStrategyGenerator,
    StrategyGenerationContext,
)
from app.services.current_actor import CurrentActor


@dataclass(slots=True)
class RealtimeLaunchPrerequisites:
    simulation: Simulation
    simulation_id: str
    setup_revision: int
    precheck: SimulationPrecheckResponse
    strategy: SimulationStrategyResponse


SETUP_DEFAULTS_BY_COUNTRY = {
    "Japan": {
        "durationMinutes": 10,
        "voiceStyle": "formal_measured",
        "voiceProfileId": "vp_japan_female_01",
    },
    "Germany": {
        "durationMinutes": 12,
        "voiceStyle": "direct_structured",
        "voiceProfileId": "vp_germany_male_01",
    },
    "UAE": {
        "durationMinutes": 10,
        "voiceStyle": "warm_relational",
        "voiceProfileId": "vp_uae_female_01",
    },
}


def _fallback_country_name(country_key: str) -> LocalizedText:
    return LocalizedText(en=country_key, zh=country_key)


def _enum_error(field_name: str, code: str, value: str) -> AppError:
    return AppError(
        status_code=400,
        code=code,
        message=f"{field_name} is not a supported value.",
        details={"field": field_name, "value": value},
    )


def _validate_enum_value(field_name: str, enum_name: str, value: str | None) -> None:
    if value is None:
        return
    if value not in load_enum_keys(enum_name):
        raise _enum_error(field_name, f"invalid_{field_name}", value)


def _get_voice_profile_by_internal_id(
    session: Session,
    voice_profile_catalog_id: str,
) -> VoiceProfileCatalog | None:
    return session.scalar(
        select(VoiceProfileCatalog)
        .where(VoiceProfileCatalog.id == voice_profile_catalog_id)
        .limit(1)
    )


def _resolve_voice_profile_catalog(
    session: Session,
    *,
    country_key: str,
    voice_profile_id: str,
) -> VoiceProfileCatalog:
    profile = session.scalar(
        select(VoiceProfileCatalog)
        .where(
            VoiceProfileCatalog.voice_profile_id == voice_profile_id,
            VoiceProfileCatalog.is_active.is_(True),
        )
        .limit(1)
    )

    if profile is None:
        raise AppError(
            status_code=400,
            code="voice_profile_not_found",
            message=f"voiceProfileId '{voice_profile_id}' does not exist.",
        )

    if profile.country_key != country_key:
        raise AppError(
            status_code=400,
            code="voice_profile_country_mismatch",
            message="voiceProfileId does not belong to the selected country.",
            details={
                "voiceProfileId": voice_profile_id,
                "countryKey": country_key,
                "profileCountryKey": profile.country_key,
            },
        )

    return profile


def _get_simulation_for_actor(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
) -> Simulation:
    simulation = session.scalar(
        select(Simulation)
        .where(Simulation.id == simulation_id, Simulation.user_id == actor.user_id)
        .limit(1)
    )

    if simulation is None:
        raise AppError(
            status_code=404,
            code="simulation_not_found",
            message=f"Simulation '{simulation_id}' was not found.",
        )

    return simulation


def _get_review_for_actor(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> Review:
    review = session.scalar(
        select(Review)
        .where(Review.id == review_id, Review.user_id == actor.user_id)
        .limit(1)
    )

    if review is None:
        raise AppError(
            status_code=404,
            code="review_not_found",
            message=f"Review '{review_id}' was not found.",
        )

    return review


def _get_uploaded_files(
    session: Session,
    simulation_id: str,
) -> list[SimulationUploadedFile]:
    return session.scalars(
        select(SimulationUploadedFile)
        .where(SimulationUploadedFile.simulation_id == simulation_id)
        .order_by(
            SimulationUploadedFile.created_at.asc(),
            SimulationUploadedFile.id.asc(),
        )
    ).all()


def _build_review_continuation_source(
    session: Session,
    review: Review,
    actor: CurrentActor,
) -> ReviewContinuationSource:
    source_simulation: Simulation | None = None
    if review.realtime_session_id is not None:
        realtime_session = session.scalar(
            select(RealtimeSession)
            .where(RealtimeSession.id == review.realtime_session_id)
            .limit(1)
        )
        if realtime_session is not None:
            source_simulation = session.scalar(
                select(Simulation)
                .where(
                    Simulation.id == realtime_session.simulation_id,
                    Simulation.user_id == actor.user_id,
                )
                .limit(1)
            )

    uploaded_files = (
        [
            UploadedContextCloneSource(
                file_name=file_record.file_name,
                content_type=file_record.content_type,
                size_bytes=file_record.size_bytes,
                upload_status=file_record.upload_status,
                storage_key=file_record.storage_key,
                parse_status=file_record.parse_status,
                source_type=file_record.source_type,
                extracted_text=file_record.extracted_text,
                extracted_summary_text=file_record.extracted_summary_text,
                extracted_excerpt_text=file_record.extracted_excerpt_text,
            )
            for file_record in _get_uploaded_files(session, source_simulation.id)
        ]
        if source_simulation is not None
        else []
    )

    return ReviewContinuationSource(
        country_key=review.country_key,
        meeting_type_key=review.meeting_type_key,
        goal_key=review.goal_key,
        duration_minutes=review.duration_minutes,
        voice_style_key=review.voice_style_key,
        voice_profile_catalog_id=review.voice_profile_catalog_id,
        constraints_text=source_simulation.constraints_text if source_simulation else None,
        uploaded_files=uploaded_files,
    )


def _invalidate_strategy(simulation: Simulation) -> None:
    simulation.strategy_payload_json = None
    simulation.strategy_generated_at = None
    simulation.strategy_for_setup_revision = None


def _has_required_setup(simulation: Simulation) -> bool:
    return all(
        [
            simulation.country_key,
            simulation.meeting_type_key,
            simulation.goal_key,
            simulation.duration_minutes is not None,
            simulation.voice_style_key,
            simulation.voice_profile_catalog_id,
        ]
    )


def _derive_simulation_status(simulation: Simulation) -> str:
    if not _has_required_setup(simulation):
        return "draft"

    if (
        simulation.strategy_payload_json
        and simulation.strategy_for_setup_revision == simulation.setup_revision
    ):
        return "strategy_ready"

    return "ready_for_strategy"


def _maybe_bump_setup_revision(simulation: Simulation, changed: bool) -> None:
    if not changed:
        return

    simulation.setup_revision += 1
    _invalidate_strategy(simulation)


def _build_uploaded_file_response(
    record: SimulationUploadedFile,
) -> SimulationUploadedFileResponse:
    return SimulationUploadedFileResponse(
        fileId=record.id,
        fileName=record.file_name,
        contentType=record.content_type,
        sizeBytes=record.size_bytes,
        sourceType=record.source_type,
        storageKey=record.storage_key,
        parseStatus=record.parse_status,
        extractedSummaryText=record.extracted_summary_text,
        extractedExcerptText=record.extracted_excerpt_text,
        status=record.upload_status,
        createdAt=record.created_at,
    )


def _parse_strategy_payload(payload: dict | None) -> SimulationStrategyResponse | None:
    if payload is None:
        return None
    return SimulationStrategyResponse.model_validate(payload)


def _build_simulation_response(
    session: Session,
    simulation: Simulation,
) -> SimulationResponse:
    voice_profile_id: str | None = None
    if simulation.voice_profile_catalog_id:
        profile = _get_voice_profile_by_internal_id(
            session,
            simulation.voice_profile_catalog_id,
        )
        voice_profile_id = profile.voice_profile_id if profile else None

    uploaded_files = [
        _build_uploaded_file_response(record)
        for record in _get_uploaded_files(session, simulation.id)
    ]

    return SimulationResponse(
        simulationId=simulation.id,
        status=_derive_simulation_status(simulation),
        setupRevision=simulation.setup_revision,
        countryKey=simulation.country_key,
        meetingType=simulation.meeting_type_key,
        goal=simulation.goal_key,
        durationMinutes=simulation.duration_minutes,
        voiceStyle=simulation.voice_style_key,
        voiceProfileId=voice_profile_id,
        constraints=simulation.constraints_text,
        uploadedFiles=uploaded_files,
        strategy=_parse_strategy_payload(simulation.strategy_payload_json),
        createdAt=simulation.created_at,
        updatedAt=simulation.updated_at,
    )


def _build_strategy_items(
    sections: list[dict],
    uploaded_files: list[SimulationUploadedFile],
    user_twin_memories: list[UserTwinMemory] | None = None,
) -> list[SimulationStrategyItem]:
    items: list[SimulationStrategyItem] = []

    for section in sections[:3]:
        bullets_en: list[str] = []
        bullets_zh: list[str] = []

        for item in section.get("items", []):
            content = item.get("content", {})
            if isinstance(content, dict):
                if content.get("en"):
                    bullets_en.append(str(content["en"]))
                if content.get("zh"):
                    bullets_zh.append(str(content["zh"]))

        if not bullets_en:
            bullets_en.append(
                "Review the latest country-specific learning notes before the session."
            )
        if not bullets_zh:
            bullets_zh = list(bullets_en)

        items.append(
            SimulationStrategyItem(
                id=str(section.get("id") or f"section-{len(items) + 1}"),
                tag=LocalizedText(en="Learning", zh="Learning"),
                title=LocalizedText.model_validate(
                    section.get("title") or {"en": "Learning focus", "zh": "Learning focus"}
                ),
                bullets=SimulationStrategyBullets(en=bullets_en, zh=bullets_zh),
            )
        )

    if uploaded_files:
        file_names = ", ".join(file_record.file_name for file_record in uploaded_files)
        uploaded_summaries = [
            _compact_strategy_text(file_record.extracted_summary_text, limit=180)
            for file_record in uploaded_files
            if file_record.extracted_summary_text
        ]
        uploaded_excerpts = [
            _compact_strategy_text(file_record.extracted_excerpt_text, limit=180)
            for file_record in uploaded_files
            if file_record.extracted_excerpt_text
        ]
        context_bullets = [
            f"Uploaded files: {file_names}",
            *[f"Summary: {summary}" for summary in uploaded_summaries[:2]],
            *[f"Evidence: {excerpt}" for excerpt in uploaded_excerpts[:2]],
        ]
        if len(context_bullets) == 1:
            context_bullets.insert(
                0,
                "Bring in the uploaded context only when it supports the current ask.",
            )
        items.append(
            SimulationStrategyItem(
                id="uploaded-context",
                tag=LocalizedText(en="Context files", zh="Context files"),
                title=LocalizedText(
                    en="Use uploaded context deliberately",
                    zh="Use uploaded context deliberately",
                ),
                bullets=SimulationStrategyBullets(
                    en=context_bullets,
                    zh=context_bullets,
                ),
            )
        )

    if user_twin_memories:
        items.append(
            SimulationStrategyItem(
                id="user-twin-memory",
                tag=LocalizedText(en="User Twin", zh="User Twin"),
                title=LocalizedText(
                    en="Watch the patterns you repeat.",
                    zh="留意你反复出现的沟通模式。",
                ),
                bullets=SimulationStrategyBullets(
                    en=[
                        (
                            f"{memory.issue_key} has appeared {memory.issue_count} time(s) "
                            f"in {memory.country_key} rounds."
                        )
                        for memory in user_twin_memories[:3]
                    ],
                    zh=[
                        (
                            f"{memory.country_key} 场景中，{memory.issue_key} 已出现 "
                            f"{memory.issue_count} 次。"
                        )
                        for memory in user_twin_memories[:3]
                    ],
                ),
            )
        )

    return items


def _compact_strategy_text(value: str | None, *, limit: int = 220) -> str:
    normalized = " ".join(str(value or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _primary_uploaded_anchor(
    uploaded_files: list[SimulationUploadedFile],
) -> tuple[SimulationUploadedFile | None, str]:
    for file_record in uploaded_files:
        anchor = _compact_strategy_text(
            file_record.extracted_summary_text or file_record.extracted_excerpt_text,
            limit=220,
        )
        if anchor:
            return file_record, anchor
    return None, ""


def _ensure_uploaded_files_are_parsed(
    uploaded_files: list[SimulationUploadedFile],
) -> None:
    failed_files = [
        {
            "fileId": file_record.id,
            "fileName": file_record.file_name,
            "parseStatus": file_record.parse_status,
        }
        for file_record in uploaded_files
        if file_record.parse_status != "ready"
    ]
    if failed_files:
        raise AppError(
            status_code=422,
            code="simulation_file_parse_failed",
            message="Every uploaded PDF or TXT file must be parsed before strategy generation.",
            details={"files": failed_files},
        )


def _build_interview_outline(
    simulation: Simulation,
    uploaded_files: list[SimulationUploadedFile],
) -> list[SimulationStrategyOutlineQuestion]:
    file_record, uploaded_anchor = _primary_uploaded_anchor(uploaded_files)
    meeting_type = simulation.meeting_type_key or "this conversation"
    goal = simulation.goal_key or "the main goal"
    country = simulation.country_key or "the target market"
    opening_anchor = uploaded_anchor or f"{goal} in {country}"

    return [
        SimulationStrategyOutlineQuestion(
            questionId="opening-context",
            stage="opening",
            prompt=(
                "Start with your opening goal, then connect it to this context: "
                f"{opening_anchor}"
            ),
            expectedSignal="User frames the objective with evidence from the uploaded brief.",
            groundingFileId=file_record.id if file_record else None,
        ),
        SimulationStrategyOutlineQuestion(
            questionId="ownership-risk",
            stage="probe",
            prompt=(
                f"Who owns the next decision in {meeting_type}, and what risk or timing point "
                "should they care about first?"
            ),
            expectedSignal="User identifies owner, risk, and next decision path.",
            groundingFileId=file_record.id if file_record else None,
        ),
        SimulationStrategyOutlineQuestion(
            questionId="specific-close",
            stage="close",
            prompt=(
                "Close with one specific next step that is dated, easy to accept, and aligned "
                f"with {goal}."
            ),
            expectedSignal="User proposes a concrete, low-friction next action.",
            groundingFileId=file_record.id if file_record else None,
        ),
    ]


def _build_strategy(
    session: Session,
    simulation: Simulation,
    voice_profile: VoiceProfileCatalog,
) -> SimulationStrategyResponse:
    latest_content = learning_service._get_latest_content(session, simulation.country_key)  # noqa: SLF001
    if latest_content is None:
        raise AppError(
            status_code=400,
            code="learning_content_not_ready",
            message=f"No published learning content exists for '{simulation.country_key}'.",
        )

    uploaded_files = _get_uploaded_files(session, simulation.id)
    user_twin_memories = session.scalars(
        select(UserTwinMemory)
        .where(
            UserTwinMemory.user_id == simulation.user_id,
            UserTwinMemory.country_key == simulation.country_key,
        )
        .order_by(
            UserTwinMemory.issue_count.desc(),
            UserTwinMemory.updated_at.desc(),
            UserTwinMemory.id.asc(),
        )
        .limit(3)
    ).all()
    items = _build_strategy_items(
        latest_content.sections_json or [],
        uploaded_files,
        user_twin_memories,
    )
    interview_outline = _build_interview_outline(simulation, uploaded_files)
    if get_settings().llm_provider_mode.strip().lower() == "openai_compatible":
        interview_outline = OpenAICompatibleStrategyGenerator(
            api_key=get_settings().llm_api_key,
            base_url=get_settings().llm_base_url,
            model=get_settings().llm_model,
            timeout_seconds=get_settings().llm_timeout_seconds,
        ).generate(
            StrategyGenerationContext(
                country_key=simulation.country_key,
                meeting_type_key=simulation.meeting_type_key or "",
                goal_key=simulation.goal_key or "",
                voice_style_key=simulation.voice_style_key or "",
                learning_bullets=[
                    str(item.get("content", {}).get("en"))
                    for section in latest_content.sections_json or []
                    for item in section.get("items", [])
                    if isinstance(item.get("content"), dict)
                    and item.get("content", {}).get("en")
                ],
                uploaded_sources=[
                    {
                        "file_id": file_record.id,
                        "file_name": file_record.file_name,
                        "text": file_record.extracted_text
                        or file_record.extracted_excerpt_text
                        or file_record.extracted_summary_text
                        or "",
                    }
                    for file_record in uploaded_files
                ],
                user_twin_memories=[
                    f"{memory.issue_key}: {memory.last_context or 'recurring pattern'} "
                    f"({memory.issue_count} occurrence(s))"
                    for memory in user_twin_memories
                ],
            )
        )
    generated_at = datetime.now(tz=UTC)

    return SimulationStrategyResponse(
        templateKey="simulation_setup_v1",
        generatedAt=generated_at,
        generatedFrom=SimulationStrategyGeneratedFrom(
            countryKey=simulation.country_key,
            meetingType=simulation.meeting_type_key or "",
            goal=simulation.goal_key or "",
            voiceStyle=simulation.voice_style_key or "",
            voiceProfileId=voice_profile.voice_profile_id,
            learningContentVersion=latest_content.content_version,
            setupRevision=simulation.setup_revision,
        ),
        summary=LocalizedText(
            en=(
                f"Anchor the {simulation.meeting_type_key} conversation around "
                f"{simulation.goal_key}, using a {simulation.voice_style_key} delivery."
            ),
            zh=(
                f"Anchor the {simulation.meeting_type_key} conversation around "
                f"{simulation.goal_key}, using a {simulation.voice_style_key} delivery."
            ),
        ),
        items=items,
        interviewOutline=interview_outline,
    )


def _apply_simulation_changes(
    session: Session,
    simulation: Simulation,
    payload: SimulationCreateRequest | SimulationPatchRequest,
    *,
    bump_revision: bool = True,
) -> bool:
    changed = False
    provided_fields = payload.model_fields_set

    if "countryKey" in provided_fields and payload.countryKey != simulation.country_key:
        country = learning_service._get_active_country(session, payload.countryKey)  # noqa: SLF001
        if country is None:
            raise AppError(
                status_code=404,
                code="country_not_found",
                message=f"Country '{payload.countryKey}' is not supported.",
            )
        simulation.country_key = payload.countryKey
        changed = True

    if "meetingType" in provided_fields:
        _validate_enum_value("meeting_type", "meeting-type", payload.meetingType)
        if payload.meetingType != simulation.meeting_type_key:
            simulation.meeting_type_key = payload.meetingType
            changed = True

    if "goal" in provided_fields:
        _validate_enum_value("goal", "goal", payload.goal)
        if payload.goal != simulation.goal_key:
            simulation.goal_key = payload.goal
            changed = True

    if (
        "durationMinutes" in provided_fields
        and payload.durationMinutes != simulation.duration_minutes
    ):
        simulation.duration_minutes = payload.durationMinutes
        changed = True

    if "voiceStyle" in provided_fields:
        _validate_enum_value("voice_style", "voice-style", payload.voiceStyle)
        if payload.voiceStyle != simulation.voice_style_key:
            simulation.voice_style_key = payload.voiceStyle
            changed = True

    if "constraints" in provided_fields and payload.constraints != simulation.constraints_text:
        simulation.constraints_text = payload.constraints
        changed = True

    if "voiceProfileId" in provided_fields:
        if payload.voiceProfileId is None:
            if simulation.voice_profile_catalog_id is not None:
                simulation.voice_profile_catalog_id = None
                changed = True
        else:
            profile = _resolve_voice_profile_catalog(
                session,
                country_key=simulation.country_key,
                voice_profile_id=payload.voiceProfileId,
            )
            if profile.id != simulation.voice_profile_catalog_id:
                simulation.voice_profile_catalog_id = profile.id
                changed = True

    if (
        "countryKey" in provided_fields
        and simulation.voice_profile_catalog_id is not None
        and "voiceProfileId" not in provided_fields
    ):
        current_profile = _get_voice_profile_by_internal_id(
            session,
            simulation.voice_profile_catalog_id,
        )
        if current_profile is not None and current_profile.country_key != simulation.country_key:
            simulation.voice_profile_catalog_id = None
            changed = True

    if bump_revision:
        _maybe_bump_setup_revision(simulation, changed)
    simulation.simulation_status = _derive_simulation_status(simulation)

    return changed


def list_voice_profiles(session: Session, country_key: str) -> list[VoiceProfileResponseItem]:
    country = learning_service._get_active_country(session, country_key)  # noqa: SLF001
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{country_key}' is not supported.",
        )

    profiles = session.scalars(
        select(VoiceProfileCatalog)
        .where(
            VoiceProfileCatalog.country_key == country_key,
            VoiceProfileCatalog.is_active.is_(True),
        )
        .order_by(VoiceProfileCatalog.gender.asc(), VoiceProfileCatalog.display_name.asc())
    ).all()

    return [
        VoiceProfileResponseItem(
            voiceProfileId=profile.voice_profile_id,
            providerVoiceId=profile.provider_voice_id,
            countryKey=profile.country_key,
            gender=profile.gender,
            locale=profile.locale,
            displayName=profile.display_name,
        )
        for profile in profiles
    ]


def get_setup_defaults(
    session: Session,
    country_key: str,
) -> SimulationSetupDefaultsResponse:
    country = learning_service._get_active_country(session, country_key)  # noqa: SLF001
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{country_key}' is not supported.",
        )

    defaults = SETUP_DEFAULTS_BY_COUNTRY.get(
        country_key,
        {
            "durationMinutes": 10,
            "voiceStyle": "formal_measured",
            "voiceProfileId": None,
        },
    )
    preferred_voice_profile_id = defaults.get("voiceProfileId")
    profile_query = select(VoiceProfileCatalog).where(
        VoiceProfileCatalog.country_key == country_key,
        VoiceProfileCatalog.is_active.is_(True),
    )
    if preferred_voice_profile_id:
        preferred_profile = session.scalar(
            profile_query.where(
                VoiceProfileCatalog.voice_profile_id == preferred_voice_profile_id,
            ).limit(1)
        )
    else:
        preferred_profile = None

    voice_profile = preferred_profile or session.scalar(
        profile_query.order_by(
            VoiceProfileCatalog.gender.asc(),
            VoiceProfileCatalog.display_name.asc(),
        ).limit(1)
    )
    if voice_profile is None:
        raise AppError(
            status_code=404,
            code="voice_profile_not_found",
            message=f"No active voice profile exists for country '{country_key}'.",
        )

    return SimulationSetupDefaultsResponse(
        countryKey=country.country_key,
        meetingType=country.default_meeting_type_key,
        goal=country.default_goal_key,
        durationMinutes=int(defaults["durationMinutes"]),
        voiceStyle=str(defaults["voiceStyle"]),
        voiceProfileId=voice_profile.voice_profile_id,
    )


def create_simulation(
    session: Session,
    actor: CurrentActor,
    payload: SimulationCreateRequest,
) -> SimulationResponse:
    country = learning_service._get_active_country(session, payload.countryKey)  # noqa: SLF001
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{payload.countryKey}' is not supported.",
        )

    simulation = Simulation(
        user_id=actor.user_id,
        country_key=payload.countryKey,
        simulation_status="draft",
        setup_revision=1,
    )
    session.add(simulation)
    session.flush()

    _apply_simulation_changes(session, simulation, payload, bump_revision=False)

    session.commit()
    session.refresh(simulation)
    return _build_simulation_response(session, simulation)


def create_simulation_from_review(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> SimulationResponse:
    review = _get_review_for_actor(session, actor, review_id)
    continuation_source = _build_review_continuation_source(session, review, actor)
    if not review_can_continue(continuation_source):
        raise AppError(
            status_code=400,
            code="review_continue_not_ready",
            message="Review does not contain enough setup to create the next simulation.",
            details={"reviewId": review_id},
        )

    seed = build_continued_simulation_seed(continuation_source)
    simulation = Simulation(
        user_id=actor.user_id,
        country_key=seed.country_key,
        meeting_type_key=seed.meeting_type_key,
        goal_key=seed.goal_key,
        duration_minutes=seed.duration_minutes,
        voice_style_key=seed.voice_style_key,
        voice_profile_catalog_id=seed.voice_profile_catalog_id,
        constraints_text=seed.constraints_text,
        simulation_status="draft",
        setup_revision=1,
    )
    session.add(simulation)
    session.flush()

    for file_record in seed.uploaded_files:
        session.add(
            SimulationUploadedFile(
                simulation_id=simulation.id,
                file_name=file_record.file_name,
                content_type=file_record.content_type,
                size_bytes=file_record.size_bytes,
                upload_status=file_record.upload_status,
                storage_key=file_record.storage_key,
                parse_status=file_record.parse_status,
                source_type=file_record.source_type,
                extracted_text=file_record.extracted_text,
                extracted_summary_text=file_record.extracted_summary_text,
                extracted_excerpt_text=file_record.extracted_excerpt_text,
            )
        )

    simulation.simulation_status = _derive_simulation_status(simulation)

    session.commit()
    session.refresh(simulation)
    return _build_simulation_response(session, simulation)


def get_simulation(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
) -> SimulationResponse:
    simulation = _get_simulation_for_actor(session, actor, simulation_id)
    return _build_simulation_response(session, simulation)


def update_simulation(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
    payload: SimulationPatchRequest,
) -> SimulationResponse:
    simulation = _get_simulation_for_actor(session, actor, simulation_id)

    _apply_simulation_changes(session, simulation, payload)

    session.commit()
    session.refresh(simulation)
    return _build_simulation_response(session, simulation)


def add_simulation_files(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
    payload: SimulationFilesRequest,
) -> SimulationResponse:
    simulation = _get_simulation_for_actor(session, actor, simulation_id)

    for file_payload in payload.files:
        extraction = extract_uploaded_file_content(
            file_payload.fileName,
            content_type=file_payload.contentType,
            size_bytes=file_payload.sizeBytes,
            source_type=file_payload.sourceType,
            text_content=file_payload.textContent,
            file_data_base64=file_payload.fileDataBase64,
        )
        session.add(
            SimulationUploadedFile(
                simulation_id=simulation.id,
                file_name=file_payload.fileName,
                content_type=file_payload.contentType,
                size_bytes=file_payload.sizeBytes,
                upload_status="registered",
                storage_key=None,
                parse_status=extraction.parse_status,
                source_type=file_payload.sourceType,
                extracted_text=extraction.extracted_text,
                extracted_summary_text=extraction.extracted_summary_text,
                extracted_excerpt_text=extraction.extracted_excerpt_text,
            )
        )

    _maybe_bump_setup_revision(simulation, bool(payload.files))
    simulation.simulation_status = _derive_simulation_status(simulation)

    session.commit()
    session.refresh(simulation)
    return _build_simulation_response(session, simulation)


def generate_simulation_strategy(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
) -> SimulationResponse:
    simulation = _get_simulation_for_actor(session, actor, simulation_id)

    if _derive_simulation_status(simulation) == "draft":
        raise AppError(
            status_code=400,
            code="simulation_not_ready_for_strategy",
            message="Simulation setup is incomplete for strategy generation.",
        )

    _ensure_uploaded_files_are_parsed(_get_uploaded_files(session, simulation.id))

    if (
        simulation.strategy_payload_json
        and simulation.strategy_for_setup_revision == simulation.setup_revision
    ):
        simulation.simulation_status = "strategy_ready"
        return _build_simulation_response(session, simulation)

    voice_profile = _get_voice_profile_by_internal_id(
        session,
        simulation.voice_profile_catalog_id or "",
    )
    if voice_profile is None:
        raise AppError(
            status_code=400,
            code="voice_profile_not_selected",
            message="voiceProfileId is required before strategy generation.",
        )

    strategy = _build_strategy(session, simulation, voice_profile)
    simulation.strategy_payload_json = strategy.model_dump(mode="json")
    simulation.strategy_generated_at = strategy.generatedAt
    simulation.strategy_for_setup_revision = simulation.setup_revision
    simulation.simulation_status = "strategy_ready"

    session.commit()
    session.refresh(simulation)
    return _build_simulation_response(session, simulation)


def validate_realtime_launch_prerequisites(
    session: Session,
    actor: CurrentActor,
    simulation_id: str,
    *,
    skip_learning_precheck: bool = False,
) -> RealtimeLaunchPrerequisites:
    simulation = _get_simulation_for_actor(session, actor, simulation_id)
    precheck = run_precheck(session, actor, simulation.country_key)

    if not precheck.ready and not (
        skip_learning_precheck and precheck.skipLearningAllowed is True
    ):
        raise AppError(
            status_code=400,
            code="learning_precheck_failed",
            message="Learning precheck must pass before realtime launch.",
            details={
                "simulationId": simulation_id,
                "reason": precheck.reason,
                "skipLearningAllowed": precheck.skipLearningAllowed,
            },
        )

    if _derive_simulation_status(simulation) == "draft":
        raise AppError(
            status_code=400,
            code="simulation_not_ready_for_launch",
            message="Simulation setup is still incomplete.",
            details={"simulationId": simulation_id},
        )

    _ensure_uploaded_files_are_parsed(_get_uploaded_files(session, simulation.id))

    if simulation.strategy_payload_json is None:
        raise AppError(
            status_code=400,
            code="simulation_strategy_missing",
            message="Strategy must be generated before realtime launch.",
            details={"simulationId": simulation_id},
        )

    if simulation.strategy_for_setup_revision != simulation.setup_revision:
        raise AppError(
            status_code=400,
            code="simulation_strategy_outdated",
            message="Strategy no longer matches the latest setup revision.",
            details={
                "simulationId": simulation_id,
                "strategyForSetupRevision": simulation.strategy_for_setup_revision,
                "setupRevision": simulation.setup_revision,
            },
        )

    strategy = _parse_strategy_payload(simulation.strategy_payload_json)
    if strategy is None:
        raise AppError(
            status_code=400,
            code="simulation_strategy_missing",
            message="Strategy must be generated before realtime launch.",
            details={"simulationId": simulation_id},
        )

    return RealtimeLaunchPrerequisites(
        simulation=simulation,
        simulation_id=simulation.id,
        setup_revision=simulation.setup_revision,
        precheck=precheck,
        strategy=strategy,
    )


def run_precheck(
    session: Session,
    actor: CurrentActor,
    country_key: str,
) -> SimulationPrecheckResponse:
    country = learning_service._get_active_country(session, country_key)  # noqa: SLF001
    if country is None:
        return SimulationPrecheckResponse(
            ready=False,
            countryKey=country_key,
            countryName=_fallback_country_name(country_key),
            reason="country_not_supported",
            learning=SimulationPrecheckLearningState(
                status="missing",
                contentVersion=None,
                completedVersion=None,
                isUpToDate=False,
            ),
            recommendedAction="change_country",
            skipLearningAllowed=False,
            warningMode=None,
        )

    latest_content = learning_service._get_latest_content(session, country_key)  # noqa: SLF001
    progress = learning_service._get_latest_progress(session, actor, country_key)  # noqa: SLF001
    latest_version = latest_content.content_version if latest_content else None
    completed_version = progress.content_version if progress else None
    is_up_to_date = bool(progress and latest_version and completed_version == latest_version)

    if is_up_to_date:
        return SimulationPrecheckResponse(
            ready=True,
            countryKey=country.country_key,
            countryName=LocalizedText.model_validate(country.country_name_json),
            reason="ready",
            learning=SimulationPrecheckLearningState(
                status="completed",
                contentVersion=latest_version,
                completedVersion=completed_version,
                isUpToDate=True,
            ),
            recommendedAction=None,
            skipLearningAllowed=None,
            warningMode=None,
        )

    status = "completed" if progress else "missing"
    reason = "learning_outdated" if progress else "learning_required"

    return SimulationPrecheckResponse(
        ready=False,
        countryKey=country.country_key,
        countryName=LocalizedText.model_validate(country.country_name_json),
        reason=reason,
        learning=SimulationPrecheckLearningState(
            status=status,
            contentVersion=latest_version,
            completedVersion=completed_version,
            isUpToDate=False,
        ),
        recommendedAction="go_to_learning",
        skipLearningAllowed=True,
        warningMode="strong_modal",
    )
