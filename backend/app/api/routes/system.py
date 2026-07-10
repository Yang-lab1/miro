from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.db.session import ping_database

router = APIRouter(tags=["system"])


@router.get("/", include_in_schema=False)
def api_root() -> dict[str, object]:
    settings = get_settings()
    db_status = {"configured": bool(settings.database_url), "reachable": False}

    try:
        db_status["reachable"] = ping_database()
    except Exception as exc:  # pragma: no cover - defensive health reporting
        db_status["error"] = exc.__class__.__name__

    return {
        "service": settings.app_name,
        "environment": settings.app_env,
        "apiPrefix": settings.api_prefix,
        "database": db_status,
        "modules": [
            "auth",
            "learning",
            "simulations",
            "realtime",
            "reviews",
            "hardware",
            "billing",
        ],
    }


@router.get("/health")
def healthcheck() -> dict[str, object]:
    settings = get_settings()
    db_reachable = False

    try:
        db_reachable = ping_database()
    except Exception:
        db_reachable = False

    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
        "databaseReachable": db_reachable,
    }


@router.get("/ready")
def readiness(response: Response) -> dict[str, object]:
    settings = get_settings()
    database_reachable = False
    try:
        database_reachable = ping_database()
    except Exception:
        database_reachable = False

    llm_provider_mode = settings.llm_provider_mode.strip().lower()
    is_production = settings.app_env.strip().lower() == "production"
    llm_configured = (
        llm_provider_mode == "openai_compatible" and bool(settings.llm_api_key.strip())
    ) or (llm_provider_mode == "rule_based" and not is_production)
    doubao_configured = bool(settings.doubao_api_key.strip()) or bool(
        settings.doubao_app_id.strip() and settings.doubao_access_token.strip()
    )
    voice_configured = doubao_configured or settings.browser_voice_fallback_enabled
    hardware_configured = settings.hardware_provider_mode.strip().lower() != "demo"
    checks = {
        "database": {"configured": bool(settings.database_url), "reachable": database_reachable},
        "llm": {
            "mode": settings.llm_provider_mode,
            "configured": llm_configured,
        },
        "doubao": {
            "resourceId": settings.doubao_resource_id,
            "configured": doubao_configured,
            "browserFallbackEnabled": settings.browser_voice_fallback_enabled,
        },
        "hardware": {
            "mode": settings.hardware_provider_mode,
            "configured": hardware_configured,
        },
    }
    ready = database_reachable and (
        not is_production
        or (llm_configured and voice_configured and hardware_configured)
    )
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if ready else "not_ready",
        "service": settings.app_name,
        "environment": settings.app_env,
        "checks": checks,
    }
