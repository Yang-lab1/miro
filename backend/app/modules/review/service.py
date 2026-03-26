from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.review import (
    ReviewDetailResponse,
    ReviewLineResponse,
    ReviewListItemResponse,
    ReviewMetricsResponse,
    ReviewSummaryResponse,
)
from app.core.errors import AppError
from app.models.review import Review, ReviewLine
from app.models.simulation import RealtimeSessionAlert, RealtimeSessionTurn, VoiceProfileCatalog
from app.modules.realtime import service as realtime_service
from app.services.current_actor import CurrentActor

REVIEW_SOURCE_REALTIME_SESSION = "realtime_session"
REVIEW_STATUS_READY = "ready"
ISSUE_PRIORITY = {
    "underdeveloped_answer": 0,
    "premature_pricing_push": 1,
    "overclaiming": 2,
}


def _get_voice_profile_id(session: Session, voice_profile_catalog_id: str | None) -> str:
    if voice_profile_catalog_id is None:
        return ""

    voice_profile = session.scalar(
        select(VoiceProfileCatalog)
        .where(VoiceProfileCatalog.id == voice_profile_catalog_id)
        .limit(1)
    )
    if voice_profile is None:
        raise AppError(
            status_code=500,
            code="voice_profile_not_found",
            message="Voice profile catalog entry for review is missing.",
            details={"voiceProfileCatalogId": voice_profile_catalog_id},
        )

    return voice_profile.voice_profile_id


def _get_review_for_actor(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> Review:
    review = session.scalar(
        select(Review)
        .where(
            Review.id == review_id,
            Review.user_id == actor.user_id,
        )
        .limit(1)
    )
    if review is None:
        raise AppError(
            status_code=404,
            code="review_not_found",
            message=f"Review '{review_id}' was not found.",
        )

    return review


def _get_existing_realtime_review(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> Review | None:
    return session.scalar(
        select(Review)
        .where(
            Review.user_id == actor.user_id,
            Review.review_source == REVIEW_SOURCE_REALTIME_SESSION,
            Review.realtime_session_id == session_id,
        )
        .limit(1)
    )


def _build_top_issue_keys(alerts: list[RealtimeSessionAlert]) -> list[str]:
    counts: dict[str, int] = {}
    first_seen_index: dict[str, int] = {}

    for index, alert in enumerate(alerts):
        counts[alert.issue_key] = counts.get(alert.issue_key, 0) + 1
        first_seen_index.setdefault(alert.issue_key, index)

    ordered = sorted(
        counts,
        key=lambda issue_key: (-counts[issue_key], first_seen_index[issue_key]),
    )
    return ordered[:3]


def _sort_alerts_for_snapshot(
    alerts: list[RealtimeSessionAlert],
    turn_index_by_id: dict[str, int],
) -> list[RealtimeSessionAlert]:
    return sorted(
        alerts,
        key=lambda alert: (
            turn_index_by_id.get(alert.turn_id or "", 10**9),
            alert.created_at,
            ISSUE_PRIORITY.get(alert.issue_key, 999),
            alert.id,
        ),
    )


def _issue_phrase(issue_key: str) -> str:
    phrases = {
        "underdeveloped_answer": "answers that stayed too thin to move the conversation forward",
        "premature_pricing_push": "pricing pressure that arrived before trust was established",
        "overclaiming": "claims that sounded more absolute than the situation supported",
    }
    return phrases.get(issue_key, "a recurring communication issue that still needs attention")


def _country_tone_sentence(country_key: str) -> str:
    if country_key == "Japan":
        return (
            "In Japan, trust and pacing matter, so it helps to hold commercial pressure until "
            "alignment feels established."
        )
    if country_key == "Germany":
        return (
            "In Germany, the conversation lands better when ownership, process, and specifics "
            "stay explicit."
        )
    if country_key == "UAE":
        return (
            "In the UAE, relationship-first pacing and a warmer tone help the conversation move "
            "without sounding abrupt."
        )
    return (
        "In this context, practical clarification and one focused next step will read more "
        "credibly than broad pressure."
    )


def _build_coach_summary(
    country_key: str,
    overall_assessment: str,
    top_issue_keys: list[str],
) -> str:
    primary_issue = top_issue_keys[0] if top_issue_keys else None
    secondary_issue = top_issue_keys[1] if len(top_issue_keys) > 1 else None

    if overall_assessment == "needs_work":
        opening = (
            f"The session lost control around {_issue_phrase(primary_issue)}."
            if primary_issue
            else "The session lost momentum in a way that needs more control."
        )
    elif overall_assessment == "promising":
        opening = (
            "The session created a strong rehearsal baseline and kept the exchange moving."
        )
    else:
        opening = (
            f"The session showed useful momentum, but {_issue_phrase(primary_issue)} still "
            "weakened the exchange."
            if primary_issue
            else "The session showed useful momentum, but it still needs sharper control."
        )

    sentences = [opening, _country_tone_sentence(country_key)]
    if secondary_issue is not None:
        sentences.append(f"A second pattern was {_issue_phrase(secondary_issue)}.")
    return " ".join(sentences)


def _build_next_step(country_key: str, top_issue_keys: list[str]) -> str:
    if top_issue_keys:
        issue_key = top_issue_keys[0]
        if issue_key == "underdeveloped_answer":
            return (
                "Next time, answer with one concrete point and one follow-up question "
                "before you pause."
            )
        if issue_key == "premature_pricing_push":
            return (
                "Next time, hold pricing until the counterpart signals enough trust to "
                "discuss commercial terms."
            )
        if issue_key == "overclaiming":
            return (
                "Next time, replace absolute claims with language that you can support and verify."
            )

    if country_key == "Japan":
        return "Next time, slow the pace and invite the partner to name the safest next step."
    if country_key == "Germany":
        return (
            "Next time, make the owner, process, and next action explicit in one concise turn."
        )
    if country_key == "UAE":
        return "Next time, reinforce rapport first and then move into one gentle clarification."
    return "Next time, keep the response concrete and end with one focused clarifying question."


def _build_review_metrics(
    turns: list[RealtimeSessionTurn],
    alerts: list[RealtimeSessionAlert],
) -> dict[str, object]:
    return {
        "turnCount": len(turns),
        "alertCount": len(alerts),
        "highSeverityCount": sum(1 for alert in alerts if alert.severity == "high"),
        "mediumSeverityCount": sum(1 for alert in alerts if alert.severity == "medium"),
        "topIssueKeys": _build_top_issue_keys(alerts),
    }


def _build_overall_assessment(metrics: dict[str, object]) -> str:
    high_severity_count = int(metrics["highSeverityCount"])
    alert_count = int(metrics["alertCount"])
    turn_count = int(metrics["turnCount"])

    if high_severity_count >= 1:
        return "needs_work"
    if alert_count == 0 and turn_count >= 4:
        return "promising"
    return "mixed"


def _build_review_summary(
    country_key: str,
    overall_assessment: str,
    top_issue_keys: list[str],
) -> dict[str, str]:
    headline = {
        "needs_work": "Needs stronger control of the conversation.",
        "mixed": "Good momentum with room to sharpen.",
        "promising": "Strong rehearsal baseline.",
    }[overall_assessment]

    return {
        "headline": headline,
        "coachSummary": _build_coach_summary(
            country_key,
            overall_assessment,
            top_issue_keys,
        ),
        "nextStep": _build_next_step(country_key, top_issue_keys),
    }


def _normalize_summary_payload(review: Review) -> ReviewSummaryResponse:
    payload = review.summary_json or {
        "headline": review.title_text,
        "coachSummary": "",
        "nextStep": "",
    }
    return ReviewSummaryResponse(
        headline=str(payload.get("headline", review.title_text)),
        coachSummary=str(payload.get("coachSummary", "")),
        nextStep=str(payload.get("nextStep", "")),
    )


def _normalize_metrics_payload(review: Review) -> ReviewMetricsResponse:
    payload = review.metrics_json or {
        "turnCount": 0,
        "alertCount": 0,
        "highSeverityCount": 0,
        "mediumSeverityCount": 0,
        "topIssueKeys": review.repeated_issues_json or [],
    }
    return ReviewMetricsResponse(
        turnCount=int(payload.get("turnCount", 0)),
        alertCount=int(payload.get("alertCount", 0)),
        highSeverityCount=int(payload.get("highSeverityCount", 0)),
        mediumSeverityCount=int(payload.get("mediumSeverityCount", 0)),
        topIssueKeys=[str(issue_key) for issue_key in payload.get("topIssueKeys", [])],
    )


def _build_review_line_response(review_line: ReviewLine, fallback_index: int) -> ReviewLineResponse:
    return ReviewLineResponse(
        lineIndex=review_line.line_index or fallback_index,
        speaker=review_line.speaker,
        turnIndex=review_line.turn_index or fallback_index,
        text=review_line.text or review_line.source_text,
        alertIssueKeys=[str(issue_key) for issue_key in review_line.alert_issue_keys_json or []],
        createdAt=review_line.created_at,
    )


def _build_review_detail_response(
    session: Session,
    review: Review,
) -> ReviewDetailResponse:
    lines = session.scalars(
        select(ReviewLine)
        .where(ReviewLine.review_id == review.id)
        .order_by(
            ReviewLine.line_index.asc(),
            ReviewLine.created_at.asc(),
            ReviewLine.id.asc(),
        )
    ).all()
    metrics = _normalize_metrics_payload(review)

    return ReviewDetailResponse(
        reviewId=review.id,
        sourceType=review.review_source,
        sourceSessionId=review.realtime_session_id or "",
        status="ready",
        countryKey=review.country_key,
        meetingType=review.meeting_type_key or "",
        goal=review.goal_key or "",
        durationMinutes=review.duration_minutes or 0,
        voiceStyle=review.voice_style_key or "",
        voiceProfileId=_get_voice_profile_id(session, review.voice_profile_catalog_id),
        setupRevision=review.setup_revision or 0,
        strategyForSetupRevision=review.strategy_for_setup_revision or 0,
        overallAssessment=review.overall_assessment or "mixed",
        summary=_normalize_summary_payload(review),
        metrics=metrics,
        lines=[
            _build_review_line_response(review_line, index)
            for index, review_line in enumerate(lines, start=1)
        ],
        createdAt=review.created_at,
        endedAt=review.ended_at,
    )


def create_review_from_realtime_session(
    session: Session,
    actor: CurrentActor,
    session_id: str,
) -> ReviewDetailResponse:
    realtime_session = realtime_service.load_realtime_session_for_actor(
        session,
        actor,
        session_id,
    )

    if realtime_session.session_status not in {"ended", "failed"}:
        raise AppError(
            status_code=400,
            code="realtime_session_not_finished",
            message="Realtime session must be finished before review snapshot can be created.",
            details={
                "sessionId": realtime_session.id,
                "status": realtime_session.session_status,
            },
        )

    existing_review = _get_existing_realtime_review(session, actor, realtime_session.id)
    if existing_review is not None:
        return _build_review_detail_response(session, existing_review)

    turns = session.scalars(
        select(RealtimeSessionTurn)
        .where(RealtimeSessionTurn.session_id == realtime_session.id)
        .order_by(
            RealtimeSessionTurn.turn_index.asc(),
            RealtimeSessionTurn.created_at.asc(),
            RealtimeSessionTurn.id.asc(),
        )
    ).all()
    alerts = session.scalars(
        select(RealtimeSessionAlert)
        .where(RealtimeSessionAlert.session_id == realtime_session.id)
        .order_by(
            RealtimeSessionAlert.created_at.asc(),
            RealtimeSessionAlert.id.asc(),
        )
    ).all()
    turn_index_by_id = {turn.id: turn.turn_index for turn in turns}
    alerts = _sort_alerts_for_snapshot(alerts, turn_index_by_id)
    metrics = _build_review_metrics(turns, alerts)
    top_issue_keys = [str(issue_key) for issue_key in metrics["topIssueKeys"]]
    overall_assessment = _build_overall_assessment(metrics)
    summary = _build_review_summary(
        realtime_session.country_key,
        overall_assessment,
        top_issue_keys,
    )

    review = Review(
        user_id=actor.user_id,
        realtime_session_id=realtime_session.id,
        device_id=None,
        review_source=REVIEW_SOURCE_REALTIME_SESSION,
        country_key=realtime_session.country_key,
        meeting_type_key=realtime_session.meeting_type_key,
        goal_key=realtime_session.goal_key,
        duration_minutes=realtime_session.duration_minutes,
        voice_style_key=realtime_session.voice_style_key,
        voice_profile_catalog_id=realtime_session.voice_profile_catalog_id,
        setup_revision=realtime_session.setup_revision,
        strategy_for_setup_revision=realtime_session.strategy_for_setup_revision,
        review_status=REVIEW_STATUS_READY,
        overall_assessment=overall_assessment,
        title_text=summary["headline"],
        score_total=None,
        summary_json=summary,
        metrics_json=metrics,
        repeated_issues_json=top_issue_keys,
        ended_at=realtime_session.ended_at,
    )
    session.add(review)
    session.flush()

    alert_issue_keys_by_turn: dict[str, list[str]] = defaultdict(list)
    for alert in alerts:
        if alert.turn_id is not None:
            alert_issue_keys_by_turn[alert.turn_id].append(alert.issue_key)

    for line_index, turn in enumerate(turns, start=1):
        text = turn.normalized_text or turn.source_text or ""
        session.add(
            ReviewLine(
                review_id=review.id,
                line_index=line_index,
                speaker=turn.speaker,
                turn_index=turn.turn_index,
                text=text,
                source_text=text,
                translation_json=None,
                tags_json=None,
                issue_key=None,
                advice_json=None,
                alert_issue_keys_json=alert_issue_keys_by_turn.get(turn.id, []),
                created_at=turn.created_at,
                updated_at=turn.created_at,
            )
        )

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing_review = _get_existing_realtime_review(session, actor, realtime_session.id)
        if existing_review is not None:
            return _build_review_detail_response(session, existing_review)
        raise

    session.refresh(review)
    return _build_review_detail_response(session, review)


def list_reviews(
    session: Session,
    actor: CurrentActor,
) -> list[ReviewListItemResponse]:
    reviews = session.scalars(
        select(Review)
        .where(Review.user_id == actor.user_id)
        .order_by(Review.created_at.desc(), Review.id.desc())
    ).all()

    responses: list[ReviewListItemResponse] = []
    for review in reviews:
        metrics = _normalize_metrics_payload(review)
        responses.append(
            ReviewListItemResponse(
                reviewId=review.id,
                sourceType=review.review_source,
                sourceSessionId=review.realtime_session_id or "",
                status="ready",
                countryKey=review.country_key,
                meetingType=review.meeting_type_key or "",
                goal=review.goal_key or "",
                overallAssessment=review.overall_assessment or "mixed",
                topIssueKeys=metrics.topIssueKeys,
                createdAt=review.created_at,
                endedAt=review.ended_at,
            )
        )

    return responses


def get_review_detail(
    session: Session,
    actor: CurrentActor,
    review_id: str,
) -> ReviewDetailResponse:
    review = _get_review_for_actor(session, actor, review_id)
    return _build_review_detail_response(session, review)
