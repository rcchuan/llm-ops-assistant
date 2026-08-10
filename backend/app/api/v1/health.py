from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    settings = get_settings()
    database_up = check_database()
    dify_base_configured = bool(settings.dify_base_url.strip())
    content = {
        "status": "ok" if database_up else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": {"status": "up" if database_up else "down"},
        "api": {"status": "up"},
        "dify_app": {"status": "configured" if dify_base_configured and settings.dify_app_api_key.get_secret_value() else "not_configured"},
        "dify_dataset": {"status": "configured" if dify_base_configured and settings.dify_dataset_api_key.get_secret_value() and settings.dify_dataset_id.strip() else "not_configured"},
    }
    return JSONResponse(status_code=200 if database_up else 503, content=content)
