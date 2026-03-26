from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas.common import LocalizedText
from app.api.schemas.learning import (
    LearningCountryResponse,
    LearningCountrySummaryResponse,
    LearningProgressResponse,
)
from app.core.errors import AppError
from app.models.learning import CountryCatalog, CountryLearningContent, UserLearningProgress
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
