from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_dify_dataset_client, require_admin
from app.core.exceptions import (
    KnowledgeEntryConflictError,
    KnowledgeEntryForbiddenError,
    KnowledgeEntryNotFoundError,
    KnowledgeEntryPersistenceError,
)
from app.db.session import get_db
from app.integrations.dify.dataset_client import DifyDatasetClient
from app.integrations.dify.dataset_exceptions import (
    DifyDatasetConfigurationError,
    DifyDatasetInvalidResponseError,
    DifyDatasetRequestError,
    DifyDatasetUncertainError,
)
from app.models.user import User
from app.repositories.knowledge_repository import KnowledgeRepository
from app.schemas.knowledge_entry import (
    KnowledgeEntryPage,
    KnowledgeEntryRead,
    KnowledgeEntryUpdate,
)
from app.services.knowledge_service import KnowledgeService


router = APIRouter(prefix="/knowledge-entries", tags=["knowledge-entries"])
PAGE_SIZE = 20


def build_service(
    session: Session,
    dataset_client: DifyDatasetClient | None = None,
) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(session), dataset_client)


@router.get("", response_model=KnowledgeEntryPage)
def list_knowledge_entries(
    page: int = Query(1, ge=1),
    user: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> KnowledgeEntryPage:
    try:
        entries, total = build_service(session).list_entries(
            user, page=page, page_size=PAGE_SIZE
        )
    except KnowledgeEntryForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except KnowledgeEntryPersistenceError:
        raise HTTPException(status_code=503, detail="候选知识查询失败，请稍后重试") from None
    return KnowledgeEntryPage(
        items=[KnowledgeEntryRead.model_validate(entry) for entry in entries],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


@router.put("/{entry_id}", response_model=KnowledgeEntryRead)
def update_knowledge_entry(
    entry_id: int,
    payload: KnowledgeEntryUpdate,
    user: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> KnowledgeEntryRead:
    try:
        entry = build_service(session).update(user, entry_id, **payload.model_dump())
    except KnowledgeEntryForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except KnowledgeEntryNotFoundError:
        raise HTTPException(status_code=404, detail="候选知识不存在") from None
    except KnowledgeEntryConflictError:
        raise HTTPException(status_code=409, detail="已同步候选不能修改") from None
    except KnowledgeEntryPersistenceError:
        raise HTTPException(status_code=503, detail="候选知识保存失败，请稍后重试") from None
    return KnowledgeEntryRead.model_validate(entry)


@router.post("/{entry_id}/sync", response_model=KnowledgeEntryRead)
def sync_knowledge_entry(
    entry_id: int,
    user: User = Depends(require_admin),
    session: Session = Depends(get_db),
    dataset_client: DifyDatasetClient = Depends(get_dify_dataset_client),
) -> KnowledgeEntryRead:
    try:
        entry = build_service(session, dataset_client).sync(user, entry_id)
    except KnowledgeEntryForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except KnowledgeEntryNotFoundError:
        raise HTTPException(status_code=404, detail="候选知识不存在") from None
    except KnowledgeEntryConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能同步") from None
    except DifyDatasetConfigurationError:
        raise HTTPException(status_code=503, detail="Dify 配置或认证失败") from None
    except DifyDatasetRequestError:
        raise HTTPException(status_code=502, detail="Dify 未接受知识文档") from None
    except DifyDatasetUncertainError:
        raise HTTPException(
            status_code=504,
            detail=(
                "同步结果不确定，请先在 Dify 控制台按 "
                f"[KE-{entry_id}] 核对后再决定是否重试"
            ),
        ) from None
    except DifyDatasetInvalidResponseError:
        raise HTTPException(
            status_code=502,
            detail=(
                "Dify 返回数据无效，请先在 Dify 控制台按 "
                f"[KE-{entry_id}] 核对后再决定是否重试"
            ),
        ) from None
    except KnowledgeEntryPersistenceError:
        raise HTTPException(
            status_code=503,
            detail=(
                "同步状态保存失败，请先在 Dify 控制台按 "
                f"[KE-{entry_id}] 核对后再决定是否重试"
            ),
        ) from None
    return KnowledgeEntryRead.model_validate(entry)
