from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas.common import LocalizedText
from app.api.schemas.learning import (
    LearningCountryResponse,
    LearningCountrySummaryResponse,
    LearningModuleItemResponse,
    LearningModuleSnapshotCountsResponse,
    LearningModulesResponse,
    LearningModuleStateResponse,
    LearningModuleStatus,
    LearningModuleTab,
    LearningProgressResponse,
)
from app.core.errors import AppError
from app.models.learning import (
    CountryCatalog,
    CountryLearningContent,
    LearningModuleCatalog,
    UserLearningModuleState,
    UserLearningProgress,
)
from app.modules.learning.modules import (
    LearningModuleAction,
    LearningModuleFilterInput,
    LearningModuleProjection,
    LearningModuleStateSnapshot,
    apply_learning_module_action,
    build_learning_module_snapshot_counts,
    derive_learning_module_state_label,
    derive_learning_module_status,
    filter_learning_module_projections,
    is_learning_module_saved,
    pick_recommended_module,
    sort_learning_module_projections,
)
from app.services.current_actor import CurrentActor


def _get_active_country(session: Session, country_key: str) -> CountryCatalog | None:
    return session.scalar(
        select(CountryCatalog)
        .where(CountryCatalog.country_key == country_key, CountryCatalog.is_active.is_(True))
        .limit(1)
    )


def _get_latest_content(
    session: Session,
    country_key: str,
) -> CountryLearningContent | None:
    return session.scalar(
        select(CountryLearningContent)
        .where(
            CountryLearningContent.country_key == country_key,
            CountryLearningContent.content_status == "published",
        )
        .order_by(desc(CountryLearningContent.content_version))
        .limit(1)
    )


def _get_latest_progress(
    session: Session,
    actor: CurrentActor,
    country_key: str,
) -> UserLearningProgress | None:
    return session.scalar(
        select(UserLearningProgress)
        .where(
            UserLearningProgress.user_id == actor.user_id,
            UserLearningProgress.country_key == country_key,
            UserLearningProgress.progress_status == "completed",
        )
        .order_by(
            desc(UserLearningProgress.content_version),
            desc(UserLearningProgress.completed_at),
        )
        .limit(1)
    )


def _localized_text(payload: dict[str, str]) -> LocalizedText:
    return LocalizedText.model_validate(payload)


def _build_progress_response(
    country: CountryCatalog,
    latest_content: CountryLearningContent | None,
    progress: UserLearningProgress | None,
) -> LearningProgressResponse:
    latest_version = latest_content.content_version if latest_content else None
    completed_version = progress.content_version if progress else None

    return LearningProgressResponse(
        countryKey=country.country_key,
        countryName=_localized_text(country.country_name_json),
        status="completed" if progress else "missing",
        contentVersion=completed_version,
        latestContentVersion=latest_version,
        completedAt=progress.completed_at if progress else None,
        expiresAt=progress.expires_at if progress else None,
        isUpToDate=bool(progress and latest_version and completed_version == latest_version),
    )


def list_learning_countries(session: Session) -> list[LearningCountrySummaryResponse]:
    countries = session.scalars(
        select(CountryCatalog)
        .where(CountryCatalog.is_active.is_(True))
        .order_by(CountryCatalog.country_key.asc())
    ).all()

    response: list[LearningCountrySummaryResponse] = []
    for country in countries:
        latest_content = _get_latest_content(session, country.country_key)
        response.append(
            LearningCountrySummaryResponse(
                countryKey=country.country_key,
                countryName=_localized_text(country.country_name_json),
                hasContent=latest_content is not None,
                latestContentVersion=latest_content.content_version if latest_content else None,
                defaultMeetingType=country.default_meeting_type_key,
                defaultGoal=country.default_goal_key,
            )
        )

    return response


def get_country_learning(session: Session, country_key: str) -> LearningCountryResponse:
    country = _get_active_country(session, country_key)
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{country_key}' is not supported.",
        )

    latest_content = _get_latest_content(session, country_key)
    if latest_content is None:
        raise AppError(
            status_code=404,
            code="learning_content_not_found",
            message=f"No published learning content exists for '{country_key}'.",
        )

    return LearningCountryResponse(
        countryKey=country.country_key,
        countryName=_localized_text(country.country_name_json),
        contentVersion=latest_content.content_version,
        defaultMeetingType=country.default_meeting_type_key,
        defaultGoal=country.default_goal_key,
        sections=latest_content.sections_json or [],
        checklist=latest_content.checklist_json or [],
    )


def get_learning_progress(
    session: Session,
    actor: CurrentActor,
    country_key: str,
) -> LearningProgressResponse:
    country = _get_active_country(session, country_key)
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{country_key}' is not supported.",
        )

    return _build_progress_response(
        country,
        _get_latest_content(session, country_key),
        _get_latest_progress(session, actor, country_key),
    )


def complete_learning_progress(
    session: Session,
    actor: CurrentActor,
    country_key: str,
    content_version: str,
) -> LearningProgressResponse:
    country = _get_active_country(session, country_key)
    if country is None:
        raise AppError(
            status_code=404,
            code="country_not_found",
            message=f"Country '{country_key}' is not supported.",
        )

    latest_content = _get_latest_content(session, country_key)
    if latest_content is None:
        raise AppError(
            status_code=400,
            code="learning_content_not_ready",
            message=f"No published learning content exists for '{country_key}'.",
        )

    if content_version != latest_content.content_version:
        raise AppError(
            status_code=400,
            code="invalid_content_version",
            message="contentVersion must match the latest published learning content.",
            details={
                "countryKey": country_key,
                "requestedVersion": content_version,
                "latestContentVersion": latest_content.content_version,
            },
        )

    progress = session.scalar(
        select(UserLearningProgress)
        .where(
            UserLearningProgress.user_id == actor.user_id,
            UserLearningProgress.country_key == country_key,
            UserLearningProgress.content_version == content_version,
        )
        .limit(1)
    )

    if progress is None:
        progress = UserLearningProgress(
            user_id=actor.user_id,
            country_key=country_key,
            content_version=content_version,
            progress_status="completed",
        )
        session.add(progress)

    now = datetime.now(tz=UTC)
    progress.progress_status = "completed"
    progress.completed_at = now
    progress.expires_at = now + timedelta(days=30)

    session.commit()
    session.refresh(progress)

    return _build_progress_response(country, latest_content, progress)


def _get_published_learning_module(
    session: Session,
    module_id: str,
) -> LearningModuleCatalog | None:
    return session.scalar(
        select(LearningModuleCatalog)
        .where(
            LearningModuleCatalog.id == module_id,
            LearningModuleCatalog.publish_status == "published",
        )
        .limit(1)
    )


def _list_published_learning_modules(session: Session) -> list[LearningModuleCatalog]:
    return session.scalars(
        select(LearningModuleCatalog)
        .where(LearningModuleCatalog.publish_status == "published")
        .order_by(
            LearningModuleCatalog.sort_order.asc(),
            LearningModuleCatalog.title_text.asc(),
            LearningModuleCatalog.id.asc(),
        )
    ).all()


def _get_learning_module_states_for_actor(
    session: Session,
    actor: CurrentActor,
    module_ids: list[str],
) -> dict[str, UserLearningModuleState]:
    if not module_ids:
        return {}

    states = session.scalars(
        select(UserLearningModuleState).where(
            UserLearningModuleState.user_id == actor.user_id,
            UserLearningModuleState.module_id.in_(module_ids),
        )
    ).all()
    return {state.module_id: state for state in states}


def _build_learning_module_state_snapshot(
    state: UserLearningModuleState | None,
) -> LearningModuleStateSnapshot:
    if state is None:
        return LearningModuleStateSnapshot()

    return LearningModuleStateSnapshot(
        saved_at=state.saved_at,
        started_at=state.started_at,
        completed_at=state.completed_at,
    )


def _build_learning_module_projection(
    module: LearningModuleCatalog,
    state: UserLearningModuleState | None,
) -> LearningModuleProjection:
    return LearningModuleProjection(
        module_id=module.id,
        country_key=module.country_key,
        title=module.title_text,
        summary=module.summary_text,
        theme=module.theme_key,
        scene=module.scene_key,
        sort_order=module.sort_order,
        state=_build_learning_module_state_snapshot(state),
    )


def _load_learning_module_projections(
    session: Session,
    actor: CurrentActor,
) -> list[LearningModuleProjection]:
    catalog = _list_published_learning_modules(session)
    states_by_module_id = _get_learning_module_states_for_actor(
        session,
        actor,
        [module.id for module in catalog],
    )
    return [
        _build_learning_module_projection(module, states_by_module_id.get(module.id))
        for module in catalog
    ]


def _build_learning_module_item_response(
    projection: LearningModuleProjection,
    *,
    recommended_module_id: str | None,
) -> LearningModuleItemResponse:
    return LearningModuleItemResponse(
        moduleId=projection.module_id,
        countryKey=projection.country_key,
        title=projection.title,
        summary=projection.summary,
        theme=projection.theme,
        scene=projection.scene,
        status=derive_learning_module_status(projection.state),
        stateLabel=derive_learning_module_state_label(projection.state),
        saved=is_learning_module_saved(projection.state),
        recommended=projection.module_id == recommended_module_id,
        sortOrder=projection.sort_order,
    )


def _build_learning_modules_response(
    projections: list[LearningModuleProjection],
    filters: LearningModuleFilterInput,
) -> LearningModulesResponse:
    snapshot_counts = LearningModuleSnapshotCountsResponse.model_validate(
        build_learning_module_snapshot_counts(projections)
    )
    filtered = filter_learning_module_projections(projections, filters)
    recommended = pick_recommended_module(filtered)
    recommended_module_id = recommended.module_id if recommended else None
    ordered = sort_learning_module_projections(
        filtered,
        recommended_module_id=recommended_module_id,
    )

    return LearningModulesResponse(
        recommendedModule=(
            _build_learning_module_item_response(
                recommended,
                recommended_module_id=recommended_module_id,
            )
            if recommended is not None
            else None
        ),
        snapshotCounts=snapshot_counts,
        items=[
            _build_learning_module_item_response(
                projection,
                recommended_module_id=recommended_module_id,
            )
            for projection in ordered
        ],
    )


def list_learning_modules(
    session: Session,
    actor: CurrentActor,
    *,
    country_key: str | None,
    theme: str | None,
    scene: str | None,
    status: LearningModuleStatus | None,
    tab: LearningModuleTab | None,
    query_text: str | None,
) -> LearningModulesResponse:
    projections = _load_learning_module_projections(session, actor)
    return _build_learning_modules_response(
        projections,
        LearningModuleFilterInput(
            country_key=country_key,
            theme=theme,
            scene=scene,
            status=status,
            tab=tab,
            query=query_text,
        ),
    )


def update_learning_module_state(
    session: Session,
    actor: CurrentActor,
    module_id: str,
    action: LearningModuleAction,
) -> LearningModuleStateResponse:
    module = _get_published_learning_module(session, module_id)
    if module is None:
        raise AppError(
            status_code=404,
            code="learning_module_not_found",
            message=f"Learning module '{module_id}' was not found.",
        )

    state = session.scalar(
        select(UserLearningModuleState)
        .where(
            UserLearningModuleState.user_id == actor.user_id,
            UserLearningModuleState.module_id == module_id,
        )
        .limit(1)
    )

    now = datetime.now(tz=UTC)
    next_state = apply_learning_module_action(
        _build_learning_module_state_snapshot(state),
        action,
        now=now,
    )

    should_persist = any(
        value is not None
        for value in (
            next_state.saved_at,
            next_state.started_at,
            next_state.completed_at,
        )
    )
    if state is None and should_persist:
        state = UserLearningModuleState(
            user_id=actor.user_id,
            module_id=module_id,
        )
        session.add(state)
        session.flush()

    if state is not None:
        state.saved_at = next_state.saved_at
        state.started_at = next_state.started_at
        state.completed_at = next_state.completed_at

    session.commit()

    projections = _load_learning_module_projections(session, actor)
    board = _build_learning_modules_response(
        projections,
        LearningModuleFilterInput(),
    )
    item = next(item for item in board.items if item.moduleId == module_id)
    return LearningModuleStateResponse(
        item=item,
        recommendedModule=board.recommendedModule,
        snapshotCounts=board.snapshotCounts,
    )
