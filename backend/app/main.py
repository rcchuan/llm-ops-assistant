from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository
from app.services.bootstrap_service import bootstrap_initial_admin

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.initial_admin_enabled:
        with SessionLocal() as session:
            bootstrap_initial_admin(UserRepository(session), settings)
    yield


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
