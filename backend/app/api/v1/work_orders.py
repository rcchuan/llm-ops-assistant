from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_password_changed
from app.core.exceptions import (
    WorkOrderAlreadyExistsError,
    WorkOrderConflictError,
    WorkOrderForbiddenError,
    WorkOrderNotFoundError,
    WorkOrderPersistenceError,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.work_order_repository import WorkOrderRepository
from app.repositories.work_order_repository import WorkOrderBundle
from app.schemas.work_order import (
    WorkOrderCreate,
    WorkOrderCreatorRead,
    WorkOrderLinkRead,
    WorkOrderLinksRequest,
    WorkOrderLinksResponse,
    WorkOrderPage,
    WorkOrderProcessingContent,
    WorkOrderQARead,
    WorkOrderRead,
    WorkOrderReopen,
    WorkOrderResolve,
)
from app.services.work_order_service import WorkOrderService, WorkOrderView


router = APIRouter(prefix="/work-orders", tags=["work-orders"])


def build_service(session: Session) -> WorkOrderService:
    return WorkOrderService(WorkOrderRepository(session))


def to_read(view: WorkOrderView) -> WorkOrderRead:
    order = view.order
    record = view.record
    return WorkOrderRead(
        id=order.id,
        qa_record=WorkOrderQARead(
            id=record.id,
            question=record.question,
            answer=record.answer,
            resources=record.retriever_resources or [],
            created_at=record.created_at,
        ),
        creator=(
            WorkOrderCreatorRead(
                username=view.creator.username,
                display_name=view.creator.display_name,
            )
            if view.creator is not None
            else None
        ),
        symptom=order.symptom,
        attempted_steps=order.attempted_steps,
        additional_notes=order.additional_notes,
        processing_notes=view.processing_notes,
        solution=view.solution,
        unresolved_note=order.unresolved_note,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post("", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        order, record = service.create(user, **payload.model_dump())
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="仅普通运维人员可创建工单") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="问答记录不存在") from None
    except WorkOrderAlreadyExistsError:
        raise HTTPException(status_code=409, detail="该问答已创建工单") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(
        service.present(
            user,
            WorkOrderBundle(order=order, record=record, creator=user),
        )
    )


@router.post("/links", response_model=WorkOrderLinksResponse)
def get_work_order_links(
    payload: WorkOrderLinksRequest,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderLinksResponse:
    try:
        links = build_service(session).get_links(user, payload.qa_record_ids)
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="仅普通运维人员可查询转单状态") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单查询失败，请稍后重试") from None
    return WorkOrderLinksResponse(
        items=[
            WorkOrderLinkRead(qa_record_id=qa_record_id, work_order_id=work_order_id)
            for qa_record_id, work_order_id in links
        ]
    )


@router.post("/{order_id}/start", response_model=WorkOrderRead)
def start_work_order(
    order_id: int,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle = service.start(user, order_id)
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能开始处理") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(service.present(user, bundle))


@router.put("/{order_id}/processing-content", response_model=WorkOrderRead)
def save_processing_content(
    order_id: int,
    payload: WorkOrderProcessingContent,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle = service.save_processing_content(
            user, order_id, **payload.model_dump()
        )
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能保存处理内容") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(service.present(user, bundle))


@router.post("/{order_id}/resolve", response_model=WorkOrderRead)
def resolve_work_order(
    order_id: int,
    payload: WorkOrderResolve,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle = service.resolve(user, order_id, **payload.model_dump())
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能标记已解决或解决方案为空") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(service.present(user, bundle))


@router.post("/{order_id}/confirm", response_model=WorkOrderRead)
def confirm_work_order(
    order_id: int,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle = service.confirm(user, order_id)
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="仅创建者可确认关闭") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能确认关闭") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(service.present(user, bundle))


@router.post("/{order_id}/reopen", response_model=WorkOrderRead)
def reopen_work_order(
    order_id: int,
    payload: WorkOrderReopen,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle = service.reopen(user, order_id, **payload.model_dump())
    except WorkOrderForbiddenError:
        raise HTTPException(status_code=403, detail="仅创建者可反馈问题仍存在") from None
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderConflictError:
        raise HTTPException(status_code=409, detail="当前状态不能退回或未解决说明为空") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单保存失败，请稍后重试") from None
    return to_read(service.present(user, bundle))


@router.get("", response_model=WorkOrderPage)
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderPage:
    service = build_service(session)
    try:
        bundles, total = service.list_orders(user, page=page, page_size=page_size)
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单查询失败，请稍后重试") from None
    return WorkOrderPage(
        items=[
            to_read(service.present(user, bundle))
            for bundle in bundles
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{order_id}", response_model=WorkOrderRead)
def get_work_order(
    order_id: int,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> WorkOrderRead:
    service = build_service(session)
    try:
        bundle: WorkOrderBundle = service.get(user, order_id)
    except WorkOrderNotFoundError:
        raise HTTPException(status_code=404, detail="工单不存在") from None
    except WorkOrderPersistenceError:
        raise HTTPException(status_code=503, detail="工单查询失败，请稍后重试") from None
    return to_read(service.present(user, bundle))
