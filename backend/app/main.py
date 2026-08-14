from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.bootstrap_service import bootstrap_initial_admin

settings = get_settings()
DEFAULT_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.initial_admin_enabled:
        with SessionLocal() as session:
            bootstrap_initial_admin(UserRepository(session), settings)
    yield


def create_app(dist_dir: str | Path | None = None) -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # API 必须先于 SPA 回退注册，确保已知接口始终由 API Router 处理。
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    resolved_dist_dir = Path(dist_dir) if dist_dir is not None else DEFAULT_DIST_DIR
    index_file = resolved_dist_dir / "index.html"
    if not index_file.is_file():
        return application

    @application.get("/assets", include_in_schema=False)
    async def missing_asset_root() -> None:
        raise HTTPException(status_code=404)

    application.mount(
        "/assets",
        StaticFiles(directory=resolved_dist_dir / "assets", check_dir=False),
        name="frontend-assets",
    )

    @application.get("/{frontend_path:path}", include_in_schema=False)
    async def serve_frontend(frontend_path: str) -> FileResponse:
        if frontend_path == "api" or frontend_path.startswith("api/"):
            raise HTTPException(status_code=404)
        if frontend_path == "assets" or frontend_path.startswith("assets/"):
            raise HTTPException(status_code=404)
        return FileResponse(index_file, media_type="text/html")

    return application


app = create_app()
