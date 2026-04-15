from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UploadedContextCloneSource:
    file_name: str
    content_type: str
    size_bytes: int
    upload_status: str
    storage_key: str | None
    parse_status: str | None
    source_type: str | None
    extracted_summary_text: str | None
    extracted_excerpt_text: str | None


@dataclass(frozen=True)
class ReviewContinuationSource:
    country_key: str | None
    meeting_type_key: str | None
    goal_key: str | None
    duration_minutes: int | None
    voice_style_key: str | None
    voice_profile_catalog_id: str | None
    constraints_text: str | None
    uploaded_files: list[UploadedContextCloneSource]


@dataclass(frozen=True)
class ContinuedSimulationSeed:
    country_key: str
    meeting_type_key: str
    goal_key: str
    duration_minutes: int
    voice_style_key: str
    voice_profile_catalog_id: str
    constraints_text: str | None
    uploaded_files: list[UploadedContextCloneSource]


def review_can_continue(source: ReviewContinuationSource) -> bool:
    return all(
        [
            source.country_key,
            source.meeting_type_key,
            source.goal_key,
            source.duration_minutes is not None,
            source.voice_style_key,
            source.voice_profile_catalog_id,
        ]
    )


def build_continued_simulation_seed(
    source: ReviewContinuationSource,
) -> ContinuedSimulationSeed:
    if not review_can_continue(source):
        raise ValueError("Review continuation source is missing required setup.")

    return ContinuedSimulationSeed(
        country_key=source.country_key or "",
        meeting_type_key=source.meeting_type_key or "",
        goal_key=source.goal_key or "",
        duration_minutes=source.duration_minutes or 0,
        voice_style_key=source.voice_style_key or "",
        voice_profile_catalog_id=source.voice_profile_catalog_id or "",
        constraints_text=source.constraints_text,
        uploaded_files=list(source.uploaded_files),
    )
