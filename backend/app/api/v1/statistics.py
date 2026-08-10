from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models.user import User
from app.repositories.statistics_repository import StatisticsRepository
from app.schemas.statistics import StatisticsOverview
from app.services.statistics_service import StatisticsService

router = APIRouter(prefix="/admin/statistics", tags=["admin-statistics"])


@router.get("/overview", response_model=StatisticsOverview)
def overview(_admin: User = Depends(require_admin), session: Session = Depends(get_db)) -> StatisticsOverview:
    return StatisticsOverview.model_validate(StatisticsService(StatisticsRepository(session)).overview())
