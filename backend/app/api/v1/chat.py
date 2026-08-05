from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_dify_client, require_password_changed
from app.core.exceptions import (
    ChatPersistenceError,
    ChatPersistenceUncertainError,
    ChatRecordNotFoundError,
)
from app.db.session import get_db
from app.integrations.dify.client import DifyClient
from app.integrations.dify.exceptions import (
    DifyConfigurationError,
    DifyInvalidResponseError,
    DifyTimeoutError,
    DifyUnavailableError,
)
from app.models.qa_record import QARecord
from app.models.user import User
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.qa_record_repository import QARecordRepository
from app.schemas.auth import MessageResponse
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRead,
    ChatMessageRequest,
    CurrentChatResponse,
    FeedbackRequest,
)
from app.services.chat_service import ChatMessageResult, ChatService


router = APIRouter(prefix="/chat", tags=["chat"])


def build_service(session: Session, dify_client: DifyClient | None = None) -> ChatService:
    return ChatService(
        ConversationRepository(session),
        QARecordRepository(session),
        dify_client,
    )


def record_to_read(record: QARecord) -> ChatMessageRead:
    return ChatMessageRead(
        id=record.id,
        question=record.question,
        answer=record.answer,
        resources=record.retriever_resources or [],
        feedback=record.feedback,
        created_at=record.created_at,
        persisted=True,
        conversation_locked=False,
    )


def result_to_read(result: ChatMessageResult) -> ChatMessageRead:
    return ChatMessageRead(
        id=result.id,
        question=result.question,
        answer=result.answer,
        resources=result.resources,
        feedback=result.feedback,
        created_at=result.created_at,
        persisted=result.persisted,
        conversation_locked=result.conversation_locked,
    )


@router.get("/current", response_model=CurrentChatResponse)
def current_chat(
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> CurrentChatResponse:
    state = build_service(session).get_current(user.id)
    return CurrentChatResponse(
        conversation_id=state.conversation_id,
        messages=[record_to_read(record) for record in state.messages],
    )


@router.post("/messages", response_model=ChatMessageRead)
def send_message(
    payload: ChatMessageRequest,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
    dify_client: DifyClient = Depends(get_dify_client),
) -> ChatMessageRead:
    try:
        result = build_service(session, dify_client).send_message(
            user.id,
            question=payload.question,
            start_new=payload.start_new,
        )
    except DifyTimeoutError:
        raise HTTPException(status_code=504, detail="回答生成超时，请稍后重试") from None
    except DifyConfigurationError:
        raise HTTPException(status_code=503, detail="问答服务未配置或认证失败") from None
    except DifyUnavailableError:
        raise HTTPException(status_code=503, detail="问答服务暂时不可用，请稍后重试") from None
    except DifyInvalidResponseError:
        raise HTTPException(
            status_code=502,
            detail="问答服务返回数据不完整，请稍后重试",
        ) from None
    return result_to_read(result)


@router.post("/new", response_model=MessageResponse)
def new_chat(
    _user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> MessageResponse:
    build_service(session).start_new_chat()
    return MessageResponse(message="已开始新对话")


@router.get("/history", response_model=ChatHistoryResponse)
def chat_history(
    limit: int = Query(50, ge=1, le=50),
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> ChatHistoryResponse:
    records = build_service(session).get_history(user.id)[:limit]
    return ChatHistoryResponse(items=[record_to_read(record) for record in records])


@router.put("/messages/{record_id}/feedback", response_model=ChatMessageRead)
def update_feedback(
    record_id: int,
    payload: FeedbackRequest,
    user: User = Depends(require_password_changed),
    session: Session = Depends(get_db),
) -> ChatMessageRead:
    try:
        record = build_service(session).update_feedback(
            user.id,
            record_id,
            payload.feedback,
        )
    except ChatRecordNotFoundError:
        raise HTTPException(status_code=404, detail="问答记录不存在") from None
    except ChatPersistenceError:
        raise HTTPException(status_code=503, detail="反馈保存失败，请稍后重试") from None
    except ChatPersistenceUncertainError:
        raise HTTPException(
            status_code=503,
            detail="反馈保存状态无法确认，请刷新页面确认",
        ) from None
    return record_to_read(record)
