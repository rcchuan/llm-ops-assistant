import logging
from dataclasses import dataclass
from datetime import datetime
from time import perf_counter

from app.core.exceptions import (
    ChatPersistenceError,
    ChatPersistenceUncertainError,
    ChatRecordNotFoundError,
    InvalidChatQuestionError,
)
from app.integrations.dify.client import DifyClient
from app.integrations.dify.exceptions import DifyConfigurationError, DifyInvalidResponseError
from app.models.conversation import Conversation, utc_now
from app.models.qa_record import FeedbackValue, QARecord
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.qa_record_repository import QARecordRepository


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CurrentChatState:
    conversation_id: int | None
    messages: list[QARecord]


@dataclass(frozen=True, slots=True)
class ChatMessageResult:
    id: int | None
    question: str
    answer: str
    resources: list[dict[str, str]]
    feedback: FeedbackValue | None
    created_at: datetime
    persisted: bool | None
    conversation_locked: bool
    dify_message_id: str | None


class ChatService:
    def __init__(
        self,
        conversations: ConversationRepository,
        records: QARecordRepository,
        dify_client: DifyClient | None = None,
    ) -> None:
        self.conversations = conversations
        self.records = records
        self.dify_client = dify_client

    def get_current(self, user_id: int) -> CurrentChatState:
        conversation = self.conversations.get_latest_by_user(user_id)
        if conversation is None:
            return CurrentChatState(conversation_id=None, messages=[])
        return CurrentChatState(
            conversation_id=conversation.id,
            messages=self.records.list_by_conversation(conversation.id, user_id),
        )

    def start_new_chat(self) -> CurrentChatState:
        return CurrentChatState(conversation_id=None, messages=[])

    def send_message(
        self,
        user_id: int,
        *,
        question: str,
        start_new: bool,
    ) -> ChatMessageResult:
        question = question.strip()
        if not question or len(question) > 1000:
            raise InvalidChatQuestionError
        if self.dify_client is None:
            raise DifyConfigurationError("问答服务未配置")
        conversation = None if start_new else self.conversations.get_latest_by_user(user_id)
        started_at = perf_counter()
        result = self.dify_client.chat(
            question=question,
            user_id=user_id,
            conversation_id=conversation.dify_conversation_id if conversation else None,
        )
        response_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        now = utc_now()

        if conversation is None:
            conversation = Conversation(
                user_id=user_id,
                dify_conversation_id=result.conversation_id,
                created_at=now,
                updated_at=now,
            )
        elif result.conversation_id != conversation.dify_conversation_id:
            raise DifyInvalidResponseError("问答服务会话数据不一致")
        else:
            conversation.updated_at = now

        resources = [
            {"document_name": item.document_name, "content": item.content}
            for item in result.resources
        ]
        record = QARecord(
            conversation_id=conversation.id or 0,
            user_id=user_id,
            question=question,
            answer=result.answer,
            dify_message_id=result.message_id,
            retriever_resources=resources,
            feedback=None,
            response_time_ms=response_time_ms,
            created_at=now,
        )
        if result.message_id is None:
            logger.warning("Dify 回答缺少 message_id：user_id=%s", user_id)

        try:
            record = self.records.persist_exchange(conversation, record)
        except ChatPersistenceUncertainError:
            logger.warning("问答已生成但保存状态无法确认：user_id=%s", user_id)
            return ChatMessageResult(
                id=None,
                question=question,
                answer=result.answer,
                resources=resources,
                feedback=None,
                created_at=now,
                persisted=None,
                conversation_locked=True,
                dify_message_id=result.message_id,
            )
        except ChatPersistenceError:
            logger.warning("问答已生成但保存失败：user_id=%s", user_id)
            return ChatMessageResult(
                id=None,
                question=question,
                answer=result.answer,
                resources=resources,
                feedback=None,
                created_at=now,
                persisted=False,
                conversation_locked=True,
                dify_message_id=result.message_id,
            )
        return ChatMessageResult(
            id=record.id,
            question=record.question,
            answer=record.answer,
            resources=record.retriever_resources,
            feedback=record.feedback,
            created_at=record.created_at,
            persisted=True,
            conversation_locked=False,
            dify_message_id=record.dify_message_id,
        )

    def get_history(self, user_id: int) -> list[QARecord]:
        return self.records.list_recent_by_user(user_id)

    def update_feedback(
        self,
        user_id: int,
        record_id: int,
        feedback: FeedbackValue,
    ) -> QARecord:
        record = self.records.get_owned_by_id(record_id, user_id)
        if record is None:
            raise ChatRecordNotFoundError
        record.feedback = feedback
        return self.records.save(record)
