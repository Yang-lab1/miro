from datetime import UTC, datetime

from app.modules.history.records import (
    HistoryRecordFilterInput,
    HistoryRecordProjection,
    filter_history_record_projections,
    sort_history_record_projections,
)
from app.modules.simulation.continuation import (
    ReviewContinuationSource,
    UploadedContextCloneSource,
    build_continued_simulation_seed,
    review_can_continue,
)


def _record(
    record_id: str,
    *,
    record_type: str,
    title: str,
    summary: str | None,
    detail: str | None,
    country_key: str | None,
    status: str,
    created_at: datetime,
) -> HistoryRecordProjection:
    return HistoryRecordProjection(
        record_id=record_id,
        record_type=record_type,
        title=title,
        summary=summary,
        detail=detail,
        country_key=country_key,
        status=status,
        created_at=created_at,
        review_id=None,
        source_session_id=None,
        overall_assessment=None,
        score=None,
        can_continue=False,
        can_open_review=False,
        can_replay=False,
    )


def test_filter_history_record_projections_supports_country_type_status_and_query() -> None:
    records = [
        _record(
            "review-1",
            record_type="review",
            title="Japan trust review",
            summary="Partner trust improved",
            detail="Coach summary",
            country_key="Japan",
            status="ready",
            created_at=datetime(2026, 4, 11, 10, 0, tzinfo=UTC),
        ),
        _record(
            "sync-1",
            record_type="hardware_sync",
            title="Upload sync complete",
            summary="Upload finished",
            detail="18 language events uploaded",
            country_key="Japan",
            status="warning",
            created_at=datetime(2026, 4, 11, 9, 0, tzinfo=UTC),
        ),
        _record(
            "review-2",
            record_type="review",
            title="Germany process review",
            summary="Ownership needs work",
            detail="Clarify next owner",
            country_key="Germany",
            status="ready",
            created_at=datetime(2026, 4, 11, 8, 0, tzinfo=UTC),
        ),
    ]

    filtered = filter_history_record_projections(
        records,
        HistoryRecordFilterInput(
            country_key="Japan",
            record_type="review",
            status="ready",
            query="trust",
        ),
    )

    assert [record.record_id for record in filtered] == ["review-1"]


def test_sort_history_record_projections_orders_newest_first() -> None:
    records = [
        _record(
            "older",
            record_type="review",
            title="Older review",
            summary=None,
            detail=None,
            country_key="Japan",
            status="ready",
            created_at=datetime(2026, 4, 11, 8, 0, tzinfo=UTC),
        ),
        _record(
            "newer",
            record_type="hardware_sync",
            title="Newer sync",
            summary=None,
            detail=None,
            country_key="Japan",
            status="healthy",
            created_at=datetime(2026, 4, 11, 9, 0, tzinfo=UTC),
        ),
    ]

    ordered = sort_history_record_projections(records)

    assert [record.record_id for record in ordered] == ["newer", "older"]


def test_build_continued_simulation_seed_copies_required_setup_and_uploaded_context() -> None:
    source = ReviewContinuationSource(
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id="voice-catalog-1",
        constraints_text="Keep the exchange measured.",
        uploaded_files=[
            UploadedContextCloneSource(
                file_name="renewal-notes.txt",
                content_type="text/plain",
                size_bytes=128,
                upload_status="registered",
                storage_key=None,
                parse_status="ready",
                source_type="manual_upload",
                extracted_summary_text="Renewal timing should stay conservative.",
                extracted_excerpt_text="Confirm the internal owner before pricing.",
            )
        ],
    )

    seed = build_continued_simulation_seed(source)

    assert seed.country_key == "Japan"
    assert seed.meeting_type_key == "first_introduction"
    assert seed.goal_key == "establish_trust_before_pricing"
    assert seed.duration_minutes == 10
    assert seed.voice_style_key == "formal_measured"
    assert seed.voice_profile_catalog_id == "voice-catalog-1"
    assert seed.constraints_text == "Keep the exchange measured."
    assert len(seed.uploaded_files) == 1
    assert seed.uploaded_files[0].file_name == "renewal-notes.txt"
    assert "conservative" in (seed.uploaded_files[0].extracted_summary_text or "").lower()


def test_review_can_continue_requires_complete_setup() -> None:
    ready_source = ReviewContinuationSource(
        country_key="Japan",
        meeting_type_key="first_introduction",
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id="voice-catalog-1",
        constraints_text=None,
        uploaded_files=[],
    )
    missing_setup_source = ReviewContinuationSource(
        country_key="Japan",
        meeting_type_key=None,
        goal_key="establish_trust_before_pricing",
        duration_minutes=10,
        voice_style_key="formal_measured",
        voice_profile_catalog_id="voice-catalog-1",
        constraints_text=None,
        uploaded_files=[],
    )

    assert review_can_continue(ready_source) is True
    assert review_can_continue(missing_setup_source) is False
