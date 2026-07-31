from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import check_database

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> JSONResponse:
    settings = get_settings()
    database_up = check_database()
    content = {
        "status": "ok" if database_up else "degraded",
        "service": settings.app_name,
        "version": settings.app_version,
        "database": {"status": "up" if database_up else "down"},
    }
    return JSONResponse(status_code=200 if database_up else 503, content=content)
