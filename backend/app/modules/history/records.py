from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

HistoryRecordType = Literal["review", "hardware_sync"]


@dataclass(frozen=True)
class HistoryRecordProjection:
    record_id: str
    record_type: HistoryRecordType
    title: str
    summary: str | None
    detail: str | None
    country_key: str | None
    status: str
    created_at: datetime
    review_id: str | None
    source_session_id: str | None
    overall_assessment: str | None
    score: int | None
    can_continue: bool
    can_open_review: bool
    can_replay: bool


@dataclass(frozen=True)
class HistoryRecordFilterInput:
    country_key: str | None = None
    record_type: HistoryRecordType | None = None
    status: str | None = None
    query: str | None = None


def filter_history_record_projections(
    projections: list[HistoryRecordProjection],
    filters: HistoryRecordFilterInput,
) -> list[HistoryRecordProjection]:
    filtered = projections

    if filters.country_key:
        filtered = [
            projection
            for projection in filtered
            if projection.country_key == filters.country_key
        ]
    if filters.record_type:
        filtered = [
            projection
            for projection in filtered
            if projection.record_type == filters.record_type
        ]
    if filters.status:
        filtered = [
            projection
            for projection in filtered
            if projection.status == filters.status
        ]
    if filters.query:
        needle = filters.query.strip().lower()
        filtered = [
            projection
            for projection in filtered
            if needle in projection.title.lower()
            or needle in (projection.summary or "").lower()
            or needle in (projection.detail or "").lower()
            or needle in (projection.country_key or "").lower()
        ]

    return filtered


def sort_history_record_projections(
    projections: list[HistoryRecordProjection],
) -> list[HistoryRecordProjection]:
    return sorted(
        projections,
        key=lambda projection: (
            projection.created_at,
            projection.record_type,
            projection.title.lower(),
            projection.record_id,
        ),
        reverse=True,
    )
