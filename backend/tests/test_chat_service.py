from collections import deque

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ChatRecordNotFoundError, InvalidChatQuestionError
from app.integrations.dify.exceptions import DifyInvalidResponseError, DifyTimeoutError
from app.integrations.dify.schemas import DifyChatResult, RetrieverResource
from app.models.qa_record import FeedbackValue
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.qa_record_repository import QARecordRepository
from app.services.chat_service import ChatService


class FakeDifyClient:
    def __init__(self, *results: DifyChatResult | Exception):
        self.results = deque(results)
        self.calls: list[dict] = []

    def chat(self, **kwargs) -> DifyChatResult:
        self.calls.append(kwargs)
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return result


def dify_result(
    conversation_id: str,
    answer: str,
    *,
    message_id: str | None = "message-1",
    resources: list[RetrieverResource] | None = None,
) -> DifyChatResult:
    return DifyChatResult(
        answer=answer,
        conversation_id=conversation_id,
        message_id=message_id,
        resources=resources or [],
    )


def make_service(db_session: Session, client: FakeDifyClient) -> ChatService:
    return ChatService(
        ConversationRepository(db_session),
        QARecordRepository(db_session),
        client,  # type: ignore[arg-type]
    )


def test_service_returns_empty_state_without_creating_conversation(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    service = make_service(db_session, FakeDifyClient())

    current = service.get_current(user.id)
    new_state = service.start_new_chat()

    assert current.conversation_id is None
    assert current.messages == []
    assert new_state.conversation_id is None
    assert new_state.messages == []
    assert ConversationRepository(db_session).get_latest_by_user(user.id) is None


def test_service_creates_continues_and_starts_new_conversation(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    client = FakeDifyClient(
        dify_result("dify-1", "第一轮回答"),
        dify_result("dify-1", "第二轮回答", message_id=None),
        dify_result("dify-2", "新对话回答"),
    )
    service = make_service(db_session, client)

    first = service.send_message(user.id, question=" 第一轮问题 ", start_new=False)
    second = service.send_message(user.id, question="第二轮问题", start_new=False)
    third = service.send_message(user.id, question="新问题", start_new=True)

    assert first.persisted is True and first.id is not None
    assert second.persisted is True and second.id is not None
    assert third.persisted is True and third.id is not None
    assert [call["conversation_id"] for call in client.calls] == [None, "dify-1", None]
    assert [call["user_id"] for call in client.calls] == [user.id] * 3
    assert first.question == "第一轮问题"
    assert second.dify_message_id is None

    current = service.get_current(user.id)
    assert [message.question for message in current.messages] == ["新问题"]
    assert service.start_new_chat().messages == []
    assert service.get_current(user.id).messages == current.messages


def test_service_does_not_save_dify_failure_or_empty_sources(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    failing = make_service(db_session, FakeDifyClient(DifyTimeoutError("timeout")))

    with pytest.raises(DifyTimeoutError):
        failing.send_message(user.id, question="问题", start_new=False)
    assert failing.get_current(user.id).messages == []

    successful = make_service(
        db_session,
        FakeDifyClient(dify_result("dify-1", "无来源回答", resources=[])),
    )
    message = successful.send_message(user.id, question="问题", start_new=False)
    assert message.persisted is True
    assert message.resources == []


def test_service_returns_unpersisted_answer_and_locks_after_database_failure(
    db_session: Session,
    add_user,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    service = make_service(
        db_session,
        FakeDifyClient(dify_result("dify-1", "已生成但保存失败")),
    )

    def fail_commit() -> None:
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    message = service.send_message(user.id, question="问题", start_new=False)

    assert message.id is None
    assert message.persisted is False
    assert message.conversation_locked is True
    assert message.answer == "已生成但保存失败"
    assert message.feedback is None


def test_service_returns_uncertain_answer_and_locks_after_refresh_failure(
    db_session: Session,
    add_user,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    client = FakeDifyClient(dify_result("dify-1", "已生成但保存状态未知"))
    service = make_service(db_session, client)

    def fail_refresh(_instance) -> None:
        raise SQLAlchemyError("secret connection detail")

    monkeypatch.setattr(db_session, "refresh", fail_refresh)
    message = service.send_message(user.id, question="问题", start_new=False)

    assert message.id is None
    assert message.persisted is None
    assert message.conversation_locked is True
    assert message.answer == "已生成但保存状态未知"
    assert message.feedback is None
    assert len(client.calls) == 1


def test_service_limits_history_and_isolates_feedback(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    other = add_user("Operator02")
    client = FakeDifyClient(
        *(dify_result("dify-1", f"回答{index:02d}") for index in range(55))
    )
    service = make_service(db_session, client)
    first_id = None
    for index in range(55):
        message = service.send_message(user.id, question=f"问题{index:02d}", start_new=False)
        first_id = first_id or message.id

    history = service.get_history(user.id)
    assert len(history) == 50
    assert [record.question for record in history[:2]] == ["问题54", "问题53"]

    updated = service.update_feedback(user.id, first_id, FeedbackValue.HELPFUL)
    assert updated.feedback is FeedbackValue.HELPFUL
    updated = service.update_feedback(user.id, first_id, FeedbackValue.UNHELPFUL)
    assert updated.feedback is FeedbackValue.UNHELPFUL
    with pytest.raises(ChatRecordNotFoundError):
        service.update_feedback(other.id, first_id, FeedbackValue.HELPFUL)


@pytest.mark.parametrize("question", ["   ", "x" * 1001])
def test_service_rejects_invalid_question_before_dify(
    db_session: Session,
    add_user,
    question: str,
) -> None:
    user = add_user("Operator01")
    client = FakeDifyClient()
    service = make_service(db_session, client)

    with pytest.raises(InvalidChatQuestionError):
        service.send_message(user.id, question=question, start_new=False)
    assert client.calls == []


def test_service_rejects_changed_dify_conversation_id_without_saving(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    service = make_service(
        db_session,
        FakeDifyClient(
            dify_result("dify-1", "第一轮"),
            dify_result("unexpected", "错误续答"),
        ),
    )
    service.send_message(user.id, question="第一轮", start_new=False)

    with pytest.raises(DifyInvalidResponseError):
        service.send_message(user.id, question="第二轮", start_new=False)
    assert [record.question for record in service.get_history(user.id)] == ["第一轮"]
