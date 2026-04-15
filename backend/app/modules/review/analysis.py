from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

DIMENSION_ORDER = (
    "goalFit",
    "cultureFit",
    "pacing",
    "clarity",
    "grounding",
    "objection",
)

DIMENSION_LABELS = {
    "goalFit": "Goal fit",
    "cultureFit": "Culture fit",
    "pacing": "Pacing",
    "clarity": "Clarity",
    "grounding": "Grounding",
    "objection": "Objection handling",
}

ISSUE_DIMENSION_IMPACT = {
    "underdeveloped_answer": {"goalFit": -10, "clarity": -14, "objection": -6},
    "premature_pricing_push": {"goalFit": -6, "cultureFit": -12, "pacing": -14},
    "overclaiming": {"clarity": -8, "grounding": -14, "cultureFit": -4},
    "soft_refusal_missed": {"cultureFit": -10, "objection": -12, "pacing": -6},
    "price_pressure": {"goalFit": -6, "cultureFit": -12, "pacing": -14},
    "repetition_loop": {"clarity": -12, "pacing": -8},
    "taboo_wording": {"cultureFit": -14, "clarity": -8},
    "pause_control": {"pacing": -12, "clarity": -4},
    "metaphor_risk": {"cultureFit": -8, "grounding": -10},
    "intensity_spike": {"pacing": -10, "cultureFit": -6, "objection": -6},
}

ISSUE_FOCUS = {
    "underdeveloped_answer": {
        "title": "Make the answer carry one concrete point",
        "detail": (
            "Answer with one specific business point before you move "
            "to a broader explanation."
        ),
        "dimensionKey": "clarity",
    },
    "premature_pricing_push": {
        "title": "Delay pricing until trust is visible",
        "detail": (
            "Hold commercial pressure until the counterpart signals "
            "enough trust to discuss pricing."
        ),
        "dimensionKey": "pacing",
    },
    "overclaiming": {
        "title": "Anchor claims in verifiable facts",
        "detail": (
            "Replace absolute language with wording that can be supported "
            "by the current context."
        ),
        "dimensionKey": "grounding",
    },
    "soft_refusal_missed": {
        "title": "Address hesitation before you advance",
        "detail": "Acknowledge the counterpart's concern before you push the conversation forward.",
        "dimensionKey": "objection",
    },
    "price_pressure": {
        "title": "Lower the commercial pressure",
        "detail": (
            "Use one softer transition before raising pricing, commitment, "
            "or closure language."
        ),
        "dimensionKey": "cultureFit",
    },
    "repetition_loop": {
        "title": "Reduce repeated pressure loops",
        "detail": "Avoid restating the same push and add one new clarifying angle instead.",
        "dimensionKey": "clarity",
    },
}

DIMENSION_FOCUS = {
    "goalFit": {
        "title": "Tie each reply back to the meeting goal",
        "detail": "Make one explicit link between the answer and the stated meeting goal.",
    },
    "cultureFit": {
        "title": "Match the country-specific tone",
        "detail": (
            "Use a lower-pressure, more locally appropriate tone before "
            "moving the meeting ahead."
        ),
    },
    "pacing": {
        "title": "Slow the pace of the exchange",
        "detail": (
            "Create space for the counterpart to respond before introducing "
            "the next commercial ask."
        ),
    },
    "clarity": {
        "title": "Make the core point easier to follow",
        "detail": (
            "Lead with one concrete answer, then add supporting context "
            "only after the main point lands."
        ),
    },
    "grounding": {
        "title": "Anchor the conversation in the brief",
        "detail": (
            "Reuse the uploaded context or known facts so the reply sounds "
            "tied to the real case."
        ),
    },
    "objection": {
        "title": "Handle resistance before pushing forward",
        "detail": (
            "Address the likely concern directly before you move into "
            "commitment or pricing language."
        ),
    },
}


@dataclass(frozen=True)
class ReviewAnalysisLineInput:
    line_index: int
    turn_index: int
    speaker: str
    text: str
    alert_issue_keys: list[str]
    created_at: datetime


@dataclass(frozen=True)
class ReviewAnalysisInput:
    country_key: str
    duration_minutes: int
    overall_assessment: str
    summary_headline: str
    summary_coach_summary: str
    turn_count: int
    alert_count: int
    high_severity_count: int
    medium_severity_count: int
    top_issue_keys: list[str]
    lines: list[ReviewAnalysisLineInput]


def _clamp_score(score: int) -> int:
    return max(20, min(96, score))


def _assessment_base_score(overall_assessment: str) -> int:
    return {
        "promising": 84,
        "mixed": 72,
        "needs_work": 58,
    }.get(overall_assessment, 70)


def _issue_counts(source: ReviewAnalysisInput) -> Counter[str]:
    counts = Counter(
        issue_key
        for line in source.lines
        for issue_key in line.alert_issue_keys
    )
    for issue_key in source.top_issue_keys:
        counts.setdefault(issue_key, 1)
    return counts


def _has_grounded_text(source: ReviewAnalysisInput) -> bool:
    haystacks = [
        source.summary_headline,
        source.summary_coach_summary,
        *[line.text for line in source.lines if line.speaker == "assistant"],
    ]
    markers = ("uploaded brief", "uploaded context", "renewal timing", "internal owner")
    normalized = " ".join(piece.lower() for piece in haystacks if piece)
    return any(marker in normalized for marker in markers)


def _build_dimension_scores(source: ReviewAnalysisInput) -> dict[str, int]:
    base = _assessment_base_score(source.overall_assessment)
    scores = {
        "goalFit": base + 2,
        "cultureFit": base,
        "pacing": base,
        "clarity": base + 1,
        "grounding": base,
        "objection": base - 2,
    }

    if source.turn_count == 0:
        scores["goalFit"] -= 4
        scores["clarity"] -= 6
        scores["objection"] -= 4
    elif source.turn_count >= 4 and source.alert_count == 0:
        for key in DIMENSION_ORDER:
            scores[key] += 4

    if _has_grounded_text(source):
        scores["grounding"] += 10
    else:
        scores["grounding"] -= 4

    counts = _issue_counts(source)
    for issue_key, count in counts.items():
        for dimension_key, penalty in ISSUE_DIMENSION_IMPACT.get(issue_key, {}).items():
            scores[dimension_key] += penalty * count

    if source.high_severity_count:
        scores["pacing"] -= 4 * source.high_severity_count
        scores["cultureFit"] -= 4 * source.high_severity_count
    if source.medium_severity_count:
        scores["clarity"] -= 2 * source.medium_severity_count

    return {key: _clamp_score(round(value)) for key, value in scores.items()}


def _score_status(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 65:
        return "watch"
    return "weak"


def _truncate_text(text: str, *, limit: int = 140) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _format_minute_label(turn_index: int, duration_minutes: int, max_turn_index: int) -> str:
    if duration_minutes <= 0 or max_turn_index <= 1 or turn_index <= 1:
        return "00:00"
    ratio = (turn_index - 1) / (max_turn_index - 1)
    total_seconds = int(round(duration_minutes * 60 * ratio))
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes:02d}:{seconds:02d}"


def _build_trend(
    source: ReviewAnalysisInput,
    overall_score: int,
) -> list[dict[str, object]]:
    user_lines = [line for line in source.lines if line.speaker == "user"]
    selected_lines = user_lines[-4:] or source.lines[-1:] or []
    if not selected_lines:
        return [
            {
                "turnIndex": 0,
                "minuteLabel": "00:00",
                "score": overall_score,
                "issueKeys": [],
            }
        ]

    max_turn_index = max((line.turn_index for line in selected_lines), default=1)
    trend: list[dict[str, object]] = []
    for line in selected_lines:
        score = _clamp_score(overall_score - len(line.alert_issue_keys) * 10)
        trend.append(
            {
                "turnIndex": line.turn_index,
                "minuteLabel": _format_minute_label(
                    line.turn_index,
                    source.duration_minutes,
                    max_turn_index,
                ),
                "score": score,
                "issueKeys": list(line.alert_issue_keys),
            }
        )
    return trend


def _build_focus_items(
    source: ReviewAnalysisInput,
    dimension_scores: dict[str, int],
) -> list[dict[str, object]]:
    focus_items: list[dict[str, object]] = []
    used_dimension_keys: set[str] = set()

    for issue_key in source.top_issue_keys:
        template = ISSUE_FOCUS.get(issue_key)
        if not template:
            continue
        dimension_key = template["dimensionKey"]
        if dimension_key in used_dimension_keys:
            continue
        focus_items.append(
            {
                "title": template["title"],
                "detail": template["detail"],
                "dimensionKey": dimension_key,
                "relatedIssueKeys": [issue_key],
            }
        )
        used_dimension_keys.add(dimension_key)
        if len(focus_items) == 3:
            return focus_items

    sorted_dimensions = sorted(
        DIMENSION_ORDER,
        key=lambda key: (dimension_scores[key], DIMENSION_ORDER.index(key)),
    )
    for dimension_key in sorted_dimensions:
        if dimension_key in used_dimension_keys:
            continue
        template = DIMENSION_FOCUS[dimension_key]
        related_issue_keys = [
            issue_key
            for issue_key in source.top_issue_keys
            if dimension_key in ISSUE_DIMENSION_IMPACT.get(issue_key, {})
        ]
        focus_items.append(
            {
                "title": template["title"],
                "detail": template["detail"],
                "dimensionKey": dimension_key,
                "relatedIssueKeys": related_issue_keys,
            }
        )
        if len(focus_items) == 3:
            break

    return focus_items or [
        {
            "title": DIMENSION_FOCUS["clarity"]["title"],
            "detail": DIMENSION_FOCUS["clarity"]["detail"],
            "dimensionKey": "clarity",
            "relatedIssueKeys": [],
        }
    ]


def _build_evidence_moments(source: ReviewAnalysisInput) -> list[dict[str, object]]:
    evidence_lines = [line for line in source.lines if line.alert_issue_keys]
    if not evidence_lines:
        return []

    max_turn_index = max((line.turn_index for line in source.lines), default=1)
    evidence: list[dict[str, object]] = []
    for line in evidence_lines[:3]:
        evidence.append(
            {
                "minuteLabel": _format_minute_label(
                    line.turn_index,
                    source.duration_minutes,
                    max_turn_index,
                ),
                "text": _truncate_text(line.text),
                "relatedIssueKeys": list(line.alert_issue_keys),
            }
        )
    return evidence


def _build_derived_insights(dimension_scores: dict[str, int]) -> dict[str, object]:
    strongest = max(
        DIMENSION_ORDER,
        key=lambda key: (dimension_scores[key], -DIMENSION_ORDER.index(key)),
    )
    weakest = min(
        DIMENSION_ORDER,
        key=lambda key: (dimension_scores[key], DIMENSION_ORDER.index(key)),
    )
    spread = max(dimension_scores.values()) - min(dimension_scores.values())
    return {
        "strongest": strongest,
        "weakest": weakest,
        "spread": spread,
    }


def build_review_analysis_snapshot(source: ReviewAnalysisInput) -> dict[str, object]:
    dimension_scores = _build_dimension_scores(source)
    dimensions = [
        {
            "dimensionKey": dimension_key,
            "label": DIMENSION_LABELS[dimension_key],
            "score": dimension_scores[dimension_key],
            "status": _score_status(dimension_scores[dimension_key]),
            "reason": DIMENSION_FOCUS[dimension_key]["detail"],
        }
        for dimension_key in DIMENSION_ORDER
    ]
    overall_score = round(sum(dimension_scores.values()) / len(dimension_scores))

    return {
        "overallScore": overall_score,
        "dimensions": dimensions,
        "trend": _build_trend(source, overall_score),
        "focusItems": _build_focus_items(source, dimension_scores),
        "evidenceMoments": _build_evidence_moments(source),
        "derivedInsights": _build_derived_insights(dimension_scores),
    }
