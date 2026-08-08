from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.api.v1.work_orders import router as work_orders_router
from app.api.v1.knowledge_entries import router as knowledge_entries_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(users_router)
api_router.include_router(work_orders_router)
api_router.include_router(knowledge_entries_router)
