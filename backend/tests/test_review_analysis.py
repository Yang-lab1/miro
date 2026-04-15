from datetime import UTC, datetime

from app.modules.review.analysis import (
    ReviewAnalysisInput,
    ReviewAnalysisLineInput,
    build_review_analysis_snapshot,
)


def _line(
    *,
    line_index: int,
    turn_index: int,
    speaker: str,
    text: str,
    alert_issue_keys: list[str] | None = None,
) -> ReviewAnalysisLineInput:
    return ReviewAnalysisLineInput(
        line_index=line_index,
        turn_index=turn_index,
        speaker=speaker,
        text=text,
        alert_issue_keys=alert_issue_keys or [],
        created_at=datetime(2026, 4, 11, 8, line_index, tzinfo=UTC),
    )


def test_build_review_analysis_snapshot_returns_complete_structure():
    payload = build_review_analysis_snapshot(
        ReviewAnalysisInput(
            country_key="Japan",
            duration_minutes=10,
            overall_assessment="mixed",
            summary_headline="Good momentum with room to sharpen.",
            summary_coach_summary=(
                "The session showed useful momentum, but pricing pressure arrived too early."
            ),
            turn_count=4,
            alert_count=2,
            high_severity_count=1,
            medium_severity_count=1,
            top_issue_keys=["premature_pricing_push", "underdeveloped_answer"],
            lines=[
                _line(
                    line_index=1,
                    turn_index=1,
                    speaker="user",
                    text="We should move to pricing today.",
                    alert_issue_keys=["premature_pricing_push"],
                ),
                _line(
                    line_index=2,
                    turn_index=2,
                    speaker="assistant",
                    text="Let's first confirm the internal owner and timeline.",
                ),
                _line(
                    line_index=3,
                    turn_index=3,
                    speaker="user",
                    text="Need more context.",
                    alert_issue_keys=["underdeveloped_answer"],
                ),
            ],
        )
    )

    assert set(payload) == {
        "overallScore",
        "dimensions",
        "trend",
        "focusItems",
        "evidenceMoments",
        "derivedInsights",
    }
    assert [item["dimensionKey"] for item in payload["dimensions"]] == [
        "goalFit",
        "cultureFit",
        "pacing",
        "clarity",
        "grounding",
        "objection",
    ]
    assert len(payload["trend"]) >= 1
    assert len(payload["focusItems"]) <= 3
    assert len(payload["evidenceMoments"]) == 2
    assert payload["derivedInsights"]["strongest"] in {
        "goalFit",
        "cultureFit",
        "pacing",
        "clarity",
        "grounding",
        "objection",
    }
    assert payload["derivedInsights"]["weakest"] in {
        "goalFit",
        "cultureFit",
        "pacing",
        "clarity",
        "grounding",
        "objection",
    }
    assert payload["derivedInsights"]["spread"] >= 0


def test_build_review_analysis_snapshot_degrades_safely_for_low_data():
    payload = build_review_analysis_snapshot(
        ReviewAnalysisInput(
            country_key="Japan",
            duration_minutes=10,
            overall_assessment="mixed",
            summary_headline="Good momentum with room to sharpen.",
            summary_coach_summary="The session ended before enough evidence was collected.",
            turn_count=0,
            alert_count=0,
            high_severity_count=0,
            medium_severity_count=0,
            top_issue_keys=[],
            lines=[],
        )
    )

    assert payload["overallScore"] >= 0
    assert len(payload["dimensions"]) == 6
    assert payload["evidenceMoments"] == []
    assert len(payload["trend"]) == 1
    assert payload["trend"][0]["minuteLabel"] == "00:00"
    assert 1 <= len(payload["focusItems"]) <= 3


def test_build_review_analysis_snapshot_uses_alert_lines_as_evidence_and_focus():
    payload = build_review_analysis_snapshot(
        ReviewAnalysisInput(
            country_key="Japan",
            duration_minutes=12,
            overall_assessment="needs_work",
            summary_headline="Needs stronger control of the conversation.",
            summary_coach_summary=(
                "The uploaded brief emphasized conservative renewal timing, but the user pushed"
                " pricing too early."
            ),
            turn_count=6,
            alert_count=3,
            high_severity_count=1,
            medium_severity_count=2,
            top_issue_keys=[
                "premature_pricing_push",
                "underdeveloped_answer",
                "overclaiming",
            ],
            lines=[
                _line(
                    line_index=1,
                    turn_index=1,
                    speaker="user",
                    text="We should lock pricing right away.",
                    alert_issue_keys=["premature_pricing_push"],
                ),
                _line(
                    line_index=3,
                    turn_index=3,
                    speaker="user",
                    text="Need more context.",
                    alert_issue_keys=["underdeveloped_answer"],
                ),
                _line(
                    line_index=5,
                    turn_index=5,
                    speaker="assistant",
                    text="Based on the uploaded brief, we should confirm the renewal owner first.",
                ),
            ],
        )
    )

    assert payload["focusItems"]
    assert payload["focusItems"][0]["relatedIssueKeys"]
    assert payload["evidenceMoments"][0]["relatedIssueKeys"]
    assert "pricing" in payload["evidenceMoments"][0]["text"].lower()
    assert any(
        item["dimensionKey"] == "grounding" and item["score"] > 0
        for item in payload["dimensions"]
    )
