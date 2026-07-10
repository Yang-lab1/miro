from datetime import UTC, datetime

from app.modules.learning.modules import (
    LearningModuleFilterInput,
    LearningModuleProjection,
    LearningModuleStateSnapshot,
    apply_learning_module_action,
    derive_learning_module_status,
    filter_learning_module_projections,
    pick_recommended_module,
)


def _projection(
    *,
    module_id: str,
    country_key: str,
    title: str,
    summary: str,
    theme: str,
    scene: str,
    sort_order: int,
    state: LearningModuleStateSnapshot | None = None,
) -> LearningModuleProjection:
    return LearningModuleProjection(
        module_id=module_id,
        country_key=country_key,
        title=title,
        summary=summary,
        theme=theme,
        scene=scene,
        sort_order=sort_order,
        state=state or LearningModuleStateSnapshot(),
    )


def test_derive_learning_module_status_variants():
    assert derive_learning_module_status(LearningModuleStateSnapshot()) == "new"
    assert derive_learning_module_status(
        LearningModuleStateSnapshot(saved_at=datetime(2026, 4, 11, tzinfo=UTC))
    ) == "saved"
    assert derive_learning_module_status(
        LearningModuleStateSnapshot(started_at=datetime(2026, 4, 11, tzinfo=UTC))
    ) == "open"
    assert derive_learning_module_status(
        LearningModuleStateSnapshot(
            saved_at=datetime(2026, 4, 11, tzinfo=UTC),
            started_at=datetime(2026, 4, 11, tzinfo=UTC),
        )
    ) == "open"
    assert derive_learning_module_status(
        LearningModuleStateSnapshot(completed_at=datetime(2026, 4, 11, tzinfo=UTC))
    ) == "completed"


def test_apply_learning_module_action_transitions_are_deterministic():
    now = datetime(2026, 4, 11, 12, 0, tzinfo=UTC)
    state = LearningModuleStateSnapshot()

    state = apply_learning_module_action(state, "save", now=now)
    assert state.saved_at == now
    assert state.started_at is None
    assert state.completed_at is None

    state = apply_learning_module_action(state, "start", now=now)
    assert state.saved_at == now
    assert state.started_at == now
    assert state.completed_at is None

    state = apply_learning_module_action(state, "complete", now=now)
    assert state.saved_at == now
    assert state.started_at == now
    assert state.completed_at == now

    state = apply_learning_module_action(state, "unsave", now=now)
    assert state.saved_at is None
    assert state.started_at == now
    assert state.completed_at == now


def test_pick_recommended_module_prefers_open_then_saved_then_new():
    projections = [
        _projection(
            module_id="mod_new",
            country_key="Japan",
            title="New",
            summary="Fresh card",
            theme="trust",
            scene="first_introduction",
            sort_order=2,
        ),
        _projection(
            module_id="mod_saved",
            country_key="Japan",
            title="Saved",
            summary="Saved card",
            theme="trust",
            scene="first_introduction",
            sort_order=3,
            state=LearningModuleStateSnapshot(saved_at=datetime(2026, 4, 11, tzinfo=UTC)),
        ),
        _projection(
            module_id="mod_open",
            country_key="Japan",
            title="Open",
            summary="In progress card",
            theme="trust",
            scene="first_introduction",
            sort_order=4,
            state=LearningModuleStateSnapshot(started_at=datetime(2026, 4, 11, tzinfo=UTC)),
        ),
    ]

    recommended = pick_recommended_module(projections)

    assert recommended is not None
    assert recommended.module_id == "mod_open"


def test_filter_learning_module_projections_respects_filters_and_query():
    projections = [
        _projection(
            module_id="mod_japan",
            country_key="Japan",
            title="Read hesitation before pricing",
            summary="Spot trust signals before price pressure.",
            theme="trust",
            scene="first_introduction",
            sort_order=1,
            state=LearningModuleStateSnapshot(started_at=datetime(2026, 4, 11, tzinfo=UTC)),
        ),
        _projection(
            module_id="mod_germany",
            country_key="Germany",
            title="Make ownership explicit",
            summary="Clarify owners and process early.",
            theme="clarity",
            scene="commercial_alignment",
            sort_order=2,
            state=LearningModuleStateSnapshot(saved_at=datetime(2026, 4, 11, tzinfo=UTC)),
        ),
        _projection(
            module_id="mod_uae",
            country_key="UAE",
            title="Lead with rapport",
            summary="Open with mutual intent before scope depth.",
            theme="rapport",
            scene="relationship_building",
            sort_order=3,
        ),
    ]

    filtered = filter_learning_module_projections(
        projections,
        LearningModuleFilterInput(
            country_key="Germany",
            theme="clarity",
            scene="commercial_alignment",
            status="saved",
            tab="saved",
            query="owner",
        ),
    )

    assert [item.module_id for item in filtered] == ["mod_germany"]
