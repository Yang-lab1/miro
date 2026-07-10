from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.user_twin import UserTwinMemoryResponse, UserTwinResponse
from app.core.errors import AppError
from app.models.review import Review
from app.models.user import UserTwinMemory
from app.services.current_actor import CurrentActor


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _risk_level(*, issue_count: int, overall_assessment: str | None) -> str:
    if overall_assessment == "needs_work" or issue_count >= 3:
        return "high"
    if issue_count >= 2 or overall_assessment == "mixed":
        return "medium"
    return "low"


def _build_memory_response(memory: UserTwinMemory) -> UserTwinMemoryResponse:
    return UserTwinMemoryResponse(
        memoryId=memory.id,
        issueKey=memory.issue_key,
        countryKey=memory.country_key,
        riskLevel=memory.risk_level,
        issueCount=memory.issue_count,
        lastContext=memory.last_context,
        lastReviewId=memory.last_review_id,
        lastSeenAt=memory.last_seen_at,
        createdAt=memory.created_at,
        updatedAt=memory.updated_at,
    )


def list_memories(
    session: Session,
    actor: CurrentActor,
    *,
    country_key: str | None = None,
) -> UserTwinResponse:
    statement = select(UserTwinMemory).where(UserTwinMemory.user_id == actor.user_id)
    if country_key:
        statement = statement.where(UserTwinMemory.country_key == country_key)
    memories = session.scalars(
        statement.order_by(
            UserTwinMemory.issue_count.desc(),
            UserTwinMemory.updated_at.desc(),
            UserTwinMemory.id.asc(),
        )
    ).all()
    return UserTwinResponse(items=[_build_memory_response(memory) for memory in memories])


def _get_review_for_actor(session: Session, actor: CurrentActor, review_id: str) -> Review:
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


def refresh_from_review(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> UserTwinResponse:
    review = _get_review_for_actor(session, actor, review_id)
    metrics = review.metrics_json or {}
    issue_keys = review.repeated_issues_json or metrics.get("topIssueKeys") or []
    unique_issue_keys = list(dict.fromkeys(str(issue_key) for issue_key in issue_keys if issue_key))
    if not unique_issue_keys:
        return list_memories(session, actor, country_key=review.country_key)

    summary = review.summary_json or {}
    context = " ".join(
        str(value).strip()
        for value in (
            summary.get("headline"),
            summary.get("coachSummary"),
            summary.get("nextStep"),
        )
        if value
    )[:2000]
    now = _now()

    for issue_key in unique_issue_keys:
        memory = session.scalar(
            select(UserTwinMemory)
            .where(
                UserTwinMemory.user_id == actor.user_id,
                UserTwinMemory.issue_key == issue_key,
                UserTwinMemory.country_key == review.country_key,
            )
            .limit(1)
        )
        if memory is None:
            memory = UserTwinMemory(
                user_id=actor.user_id,
                issue_key=issue_key,
                country_key=review.country_key,
                risk_level=_risk_level(
                    issue_count=1,
                    overall_assessment=review.overall_assessment,
                ),
                issue_count=1,
                last_context=context or None,
                last_review_id=review.id,
                last_seen_at=now,
            )
            session.add(memory)
            continue

        if memory.last_review_id == review.id:
            continue

        memory.issue_count = int(memory.issue_count or 0) + 1
        memory.risk_level = _risk_level(
            issue_count=memory.issue_count,
            overall_assessment=review.overall_assessment,
        )
        memory.last_context = context or memory.last_context
        memory.last_review_id = review.id
        memory.last_seen_at = now

    session.commit()
    return list_memories(session, actor, country_key=review.country_key)
