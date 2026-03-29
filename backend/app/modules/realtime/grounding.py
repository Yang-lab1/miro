from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.simulation import SimulationStrategyResponse
from app.core.errors import AppError
from app.models.simulation import RealtimeSession, Simulation, SimulationUploadedFile
from app.modules.realtime.providers.base import (
    RealtimeGroundingContext,
    RealtimeGroundingFileContext,
)


def _load_simulation(
    session: Session,
    simulation_id: str,
) -> Simulation:
    simulation = session.scalar(
        select(Simulation).where(Simulation.id == simulation_id).limit(1)
    )
    if simulation is None:
        raise AppError(
            status_code=500,
            code="realtime_simulation_missing",
            message="Realtime session simulation context is missing.",
            details={"simulationId": simulation_id},
        )
    return simulation


def _load_uploaded_files(
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


def _parse_strategy_payload(
    payload: dict | None,
) -> SimulationStrategyResponse | None:
    if payload is None:
        return None
    try:
        return SimulationStrategyResponse.model_validate(payload)
    except ValidationError:
        return None


def _build_uploaded_context_summary(
    uploaded_files: list[SimulationUploadedFile],
) -> str | None:
    summaries = [
        str(file_record.extracted_summary_text).strip()
        for file_record in uploaded_files
        if file_record.extracted_summary_text
    ]
    if not summaries:
        return None
    return " ".join(summaries[:2])


def _build_uploaded_context_excerpts(
    uploaded_files: list[SimulationUploadedFile],
) -> list[str]:
    excerpts = [
        str(file_record.extracted_excerpt_text).strip()
        for file_record in uploaded_files
        if file_record.extracted_excerpt_text
    ]
    return excerpts[:3]


def build_realtime_grounding_context(
    session: Session,
    realtime_session: RealtimeSession,
) -> RealtimeGroundingContext:
    simulation = _load_simulation(session, realtime_session.simulation_id)
    uploaded_files = _load_uploaded_files(session, simulation.id)
    strategy = _parse_strategy_payload(simulation.strategy_payload_json)

    strategy_bullets_en: list[str] = []
    if strategy is not None:
        for item in strategy.items:
            strategy_bullets_en.extend(item.bullets.en)

    uploaded_context_summary_en = _build_uploaded_context_summary(uploaded_files)
    uploaded_context_excerpts_en = _build_uploaded_context_excerpts(uploaded_files)

    return RealtimeGroundingContext(
        simulation_id=simulation.id,
        country_key=realtime_session.country_key,
        meeting_type_key=realtime_session.meeting_type_key,
        goal_key=realtime_session.goal_key,
        duration_minutes=realtime_session.duration_minutes,
        voice_style_key=realtime_session.voice_style_key,
        setup_revision=realtime_session.setup_revision,
        strategy_for_setup_revision=realtime_session.strategy_for_setup_revision,
        strategy_summary_en=strategy.summary.en if strategy is not None else None,
        strategy_bullets_en=strategy_bullets_en,
        uploaded_files=[
            RealtimeGroundingFileContext(
                file_id=file_record.id,
                file_name=file_record.file_name,
                content_type=file_record.content_type,
                size_bytes=file_record.size_bytes,
                source_type=file_record.source_type,
                storage_key=file_record.storage_key,
                parse_status=file_record.parse_status,
                upload_status=file_record.upload_status,
                extracted_summary_text=file_record.extracted_summary_text,
                extracted_excerpt_text=file_record.extracted_excerpt_text,
            )
            for file_record in uploaded_files
        ],
        uploaded_context_summary_en=uploaded_context_summary_en,
        uploaded_context_excerpts_en=uploaded_context_excerpts_en,
    )
