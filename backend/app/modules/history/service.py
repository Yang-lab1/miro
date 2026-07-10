from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.history import HistoryRecordResponse, HistoryRecordsResponse
from app.models.hardware import Device, DeviceSyncEvent
from app.models.review import Review
from app.modules.history.records import (
    HistoryRecordFilterInput,
    HistoryRecordProjection,
    filter_history_record_projections,
    sort_history_record_projections,
)
from app.modules.simulation.continuation import ReviewContinuationSource, review_can_continue
from app.services.current_actor import CurrentActor


def _review_summary(review: Review) -> str | None:
    payload = review.summary_json or {}
    value = payload.get("headline")
    return str(value) if value else None


def _review_detail(review: Review) -> str | None:
    payload = review.summary_json or {}
    value = payload.get("coachSummary")
    return str(value) if value else None


def _build_review_continuation_source(review: Review) -> ReviewContinuationSource:
    return ReviewContinuationSource(
        country_key=review.country_key,
        meeting_type_key=review.meeting_type_key,
        goal_key=review.goal_key,
        duration_minutes=review.duration_minutes,
        voice_style_key=review.voice_style_key,
        voice_profile_catalog_id=review.voice_profile_catalog_id,
        constraints_text=None,
        uploaded_files=[],
    )


def _build_review_projection(review: Review) -> HistoryRecordProjection:
    continuation_source = _build_review_continuation_source(review)
    return HistoryRecordProjection(
        record_id=review.id,
        record_type="review",
        title=review.title_text,
        summary=_review_summary(review),
        detail=_review_detail(review),
        country_key=review.country_key,
        status=review.review_status,
        created_at=review.created_at,
        review_id=review.id,
        source_session_id=review.realtime_session_id,
        overall_assessment=review.overall_assessment,
        score=review.score_total,
        can_continue=review_can_continue(continuation_source),
        can_open_review=True,
        can_replay=bool(review.realtime_session_id),
    )


def _sync_detail(event: DeviceSyncEvent) -> str | None:
    payload = event.payload_json or {}
    detail = payload.get("detailText")
    return str(detail) if detail else None


def _build_hardware_sync_projection(
    event: DeviceSyncEvent,
    linked_review: Review | None,
) -> HistoryRecordProjection:
    continuation_source = (
        _build_review_continuation_source(linked_review)
        if linked_review is not None
        else ReviewContinuationSource(
            country_key=None,
            meeting_type_key=None,
            goal_key=None,
            duration_minutes=None,
            voice_style_key=None,
            voice_profile_catalog_id=None,
            constraints_text=None,
            uploaded_files=[],
        )
    )
    return HistoryRecordProjection(
        record_id=event.id,
        record_type="hardware_sync",
        title=event.summary_text or "Demo sync completed",
        summary=event.summary_text,
        detail=_sync_detail(event),
        country_key=linked_review.country_key if linked_review is not None else None,
        status=event.health_status,
        created_at=event.created_at,
        review_id=linked_review.id if linked_review is not None else None,
        source_session_id=linked_review.realtime_session_id if linked_review is not None else None,
        overall_assessment=linked_review.overall_assessment if linked_review is not None else None,
        score=linked_review.score_total if linked_review is not None else None,
        can_continue=linked_review is not None and review_can_continue(continuation_source),
        can_open_review=linked_review is not None,
        can_replay=False,
    )


def _list_review_projections(
    session: Session,
    actor: CurrentActor,
) -> list[HistoryRecordProjection]:
    reviews = session.scalars(
        select(Review)
        .where(Review.user_id == actor.user_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()
    return [_build_review_projection(review) for review in reviews]


def _list_hardware_sync_projections(
    session: Session,
    actor: CurrentActor,
) -> list[HistoryRecordProjection]:
    rows = session.execute(
        select(DeviceSyncEvent, Review)
        .join(Device, Device.id == DeviceSyncEvent.device_id)
        .outerjoin(Review, Review.id == DeviceSyncEvent.review_id)
        .where(Device.user_id == actor.user_id)
        .order_by(DeviceSyncEvent.created_at.desc(), DeviceSyncEvent.id.desc())
    ).all()
    return [
        _build_hardware_sync_projection(event, review)
        for event, review in rows
    ]


def list_history_records(
    session: Session,
    actor: CurrentActor,
    *,
    country_key: str | None,
    record_type: str | None,
    status: str | None,
    query_text: str | None,
) -> HistoryRecordsResponse:
    projections = [
        *_list_review_projections(session, actor),
        *_list_hardware_sync_projections(session, actor),
    ]
    filtered = filter_history_record_projections(
        projections,
        HistoryRecordFilterInput(
            country_key=country_key,
            record_type=record_type,
            status=status,
            query=query_text,
        ),
    )
    ordered = sort_history_record_projections(filtered)
    return HistoryRecordsResponse(
        items=[
            HistoryRecordResponse(
                recordId=projection.record_id,
                recordType=projection.record_type,
                title=projection.title,
                summary=projection.summary,
                detail=projection.detail,
                countryKey=projection.country_key,
                status=projection.status,
                createdAt=projection.created_at,
                reviewId=projection.review_id,
                sourceSessionId=projection.source_session_id,
                overallAssessment=projection.overall_assessment,
                score=projection.score,
                canContinue=projection.can_continue,
                canOpenReview=projection.can_open_review,
                canReplay=projection.can_replay,
            )
            for projection in ordered
        ]
    )
