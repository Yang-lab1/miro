from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Literal

LearningModuleStatus = Literal["new", "saved", "open", "completed"]
LearningModuleTab = Literal["all", "recommended", "new", "saved", "open", "completed"]
LearningModuleAction = Literal["start", "save", "unsave", "complete"]

STATE_LABELS: dict[LearningModuleStatus, str] = {
    "new": "New",
    "saved": "Saved",
    "open": "In progress",
    "completed": "Completed",
}

STATUS_PRIORITY: dict[LearningModuleStatus, int] = {
    "open": 0,
    "saved": 1,
    "new": 2,
    "completed": 3,
}


@dataclass(frozen=True)
class LearningModuleStateSnapshot:
    saved_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class LearningModuleProjection:
    module_id: str
    country_key: str
    title: str
    summary: str
    theme: str
    scene: str
    sort_order: int
    state: LearningModuleStateSnapshot


@dataclass(frozen=True)
class LearningModuleFilterInput:
    country_key: str | None = None
    theme: str | None = None
    scene: str | None = None
    status: LearningModuleStatus | None = None
    tab: LearningModuleTab | None = None
    query: str | None = None


def derive_learning_module_status(state: LearningModuleStateSnapshot) -> LearningModuleStatus:
    if state.completed_at is not None:
        return "completed"
    if state.started_at is not None:
        return "open"
    if state.saved_at is not None:
        return "saved"
    return "new"


def derive_learning_module_state_label(state: LearningModuleStateSnapshot) -> str:
    return STATE_LABELS[derive_learning_module_status(state)]


def is_learning_module_saved(state: LearningModuleStateSnapshot) -> bool:
    return state.saved_at is not None


def apply_learning_module_action(
    state: LearningModuleStateSnapshot,
    action: LearningModuleAction,
    *,
    now: datetime,
) -> LearningModuleStateSnapshot:
    if action == "save":
        return replace(state, saved_at=state.saved_at or now)
    if action == "unsave":
        return replace(state, saved_at=None)
    if action == "start":
        return replace(state, started_at=state.started_at or now)
    return replace(
        state,
        started_at=state.started_at or now,
        completed_at=state.completed_at or now,
    )


def filter_learning_module_projections(
    projections: list[LearningModuleProjection],
    filters: LearningModuleFilterInput,
) -> list[LearningModuleProjection]:
    filtered = projections

    if filters.country_key:
        filtered = [item for item in filtered if item.country_key == filters.country_key]
    if filters.theme:
        filtered = [item for item in filtered if item.theme == filters.theme]
    if filters.scene:
        filtered = [item for item in filtered if item.scene == filters.scene]
    if filters.query:
        needle = filters.query.strip().lower()
        filtered = [
            item
            for item in filtered
            if needle in item.title.lower() or needle in item.summary.lower()
        ]
    if filters.status:
        filtered = [
            item
            for item in filtered
            if derive_learning_module_status(item.state) == filters.status
        ]

    if filters.tab and filters.tab != "all":
        if filters.tab == "recommended":
            recommended = pick_recommended_module(filtered)
            return [recommended] if recommended is not None else []
        filtered = [
            item
            for item in filtered
            if derive_learning_module_status(item.state) == filters.tab
        ]

    return filtered


def pick_recommended_module(
    projections: list[LearningModuleProjection],
) -> LearningModuleProjection | None:
    if not projections:
        return None

    return min(
        projections,
        key=lambda item: (
            STATUS_PRIORITY[derive_learning_module_status(item.state)],
            item.sort_order,
            item.title.lower(),
        ),
    )


def sort_learning_module_projections(
    projections: list[LearningModuleProjection],
    *,
    recommended_module_id: str | None,
) -> list[LearningModuleProjection]:
    return sorted(
        projections,
        key=lambda item: (
            0 if item.module_id == recommended_module_id else 1,
            STATUS_PRIORITY[derive_learning_module_status(item.state)],
            item.sort_order,
            item.title.lower(),
        ),
    )


def build_learning_module_snapshot_counts(
    projections: list[LearningModuleProjection],
) -> dict[str, int]:
    counts = {"open": 0, "new": 0, "saved": 0}
    for item in projections:
        status = derive_learning_module_status(item.state)
        if status in counts:
            counts[status] += 1
    return counts
