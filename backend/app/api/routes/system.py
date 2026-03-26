from fastapi import APIRouter

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
