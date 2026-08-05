from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ChatPersistenceError, ChatPersistenceUncertainError
from app.models.conversation import Conversation
from app.models.qa_record import FeedbackValue, QARecord
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.qa_record_repository import QARecordRepository


def make_conversation(user_id: int, dify_id: str, updated_at: datetime) -> Conversation:
    return Conversation(
        user_id=user_id,
        dify_conversation_id=dify_id,
        created_at=updated_at,
        updated_at=updated_at,
    )


def make_record(user_id: int, question: str, created_at: datetime) -> QARecord:
    return QARecord(
        user_id=user_id,
        question=question,
        answer=f"{question} 的回答",
        dify_message_id=None,
        retriever_resources=[],
        response_time_ms=10,
        created_at=created_at,
    )


def test_repositories_persist_exchange_and_enforce_conversation_ownership(
    db_session: Session,
    add_user,
) -> None:
    first_user = add_user("Operator01")
    second_user = add_user("Operator02")
    conversations = ConversationRepository(db_session)
    records = QARecordRepository(db_session)
    now = datetime(2026, 8, 4, 12, 0, 0)

    older = make_conversation(first_user.id, "dify-old", now - timedelta(minutes=1))
    records.persist_exchange(
        older,
        make_record(first_user.id, "旧问题", now - timedelta(minutes=1)),
    )
    latest = make_conversation(first_user.id, "dify-latest", now)
    latest_record = records.persist_exchange(
        latest,
        make_record(first_user.id, "新问题", now),
    )

    assert conversations.get_latest_by_user(first_user.id) is latest
    assert conversations.get_owned_by_id(latest.id, first_user.id) is latest
    assert conversations.get_owned_by_id(latest.id, second_user.id) is None
    assert records.get_owned_by_id(latest_record.id, first_user.id) is latest_record
    assert records.get_owned_by_id(latest_record.id, second_user.id) is None


def test_repositories_return_latest_50_in_required_order(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    other = add_user("Operator02")
    conversations = ConversationRepository(db_session)
    records = QARecordRepository(db_session)
    start = datetime(2026, 8, 4, 12, 0, 0)
    conversation = make_conversation(user.id, "dify-1", start)

    for index in range(55):
        conversation.updated_at = start + timedelta(seconds=index)
        records.persist_exchange(
            conversation,
            make_record(user.id, f"问题{index:02d}", start + timedelta(seconds=index)),
        )
    other_conversation = make_conversation(other.id, "dify-other", start)
    records.persist_exchange(
        other_conversation,
        make_record(other.id, "他人问题", start),
    )

    current = records.list_by_conversation(conversation.id, user.id, limit=50)
    history = records.list_recent_by_user(user.id, limit=50)

    assert [record.question for record in current] == [
        f"问题{index:02d}" for index in range(5, 55)
    ]
    assert [record.question for record in history] == [
        f"问题{index:02d}" for index in range(54, 4, -1)
    ]
    assert conversations.get_latest_by_user(other.id) is other_conversation
    assert all(record.user_id == user.id for record in history)


def test_repository_saves_feedback_and_rolls_back_failed_first_exchange(
    db_session: Session,
    add_user,
) -> None:
    user = add_user("Operator01")
    conversations = ConversationRepository(db_session)
    records = QARecordRepository(db_session)
    now = datetime(2026, 8, 4, 12, 0, 0)

    conversation = make_conversation(user.id, "dify-1", now)
    record = records.persist_exchange(
        conversation,
        make_record(user.id, "问题", now),
    )
    record.feedback = FeedbackValue.HELPFUL
    records.save(record)
    record.feedback = FeedbackValue.UNHELPFUL
    records.save(record)
    assert records.get_owned_by_id(record.id, user.id).feedback is FeedbackValue.UNHELPFUL

    other = add_user("Operator02")
    failed_conversation = make_conversation(other.id, "dify-failed", now)
    invalid_record = make_record(other.id, "失败问题", now)
    invalid_record.answer = None  # type: ignore[assignment]
    with pytest.raises(ChatPersistenceError):
        records.persist_exchange(failed_conversation, invalid_record)

    assert conversations.get_latest_by_user(other.id) is None


@pytest.mark.parametrize("failed_refresh", ["conversation", "record"])
def test_persist_exchange_reports_uncertain_after_commit_when_refresh_fails(
    db_session: Session,
    add_user,
    monkeypatch,
    failed_refresh: str,
) -> None:
    user = add_user("Operator01")
    records = QARecordRepository(db_session)
    now = datetime(2026, 8, 4, 12, 0, 0)
    conversation = make_conversation(user.id, "dify-1", now)
    record = make_record(user.id, "提交后刷新失败", now)

    original_refresh = db_session.refresh

    def fail_selected_refresh(instance) -> None:
        if failed_refresh == "conversation" and instance is conversation:
            raise SQLAlchemyError("secret connection detail")
        if failed_refresh == "record" and instance is record:
            raise SQLAlchemyError("secret connection detail")
        original_refresh(instance)

    monkeypatch.setattr(db_session, "refresh", fail_selected_refresh)

    with pytest.raises(ChatPersistenceUncertainError):
        records.persist_exchange(conversation, record)

    db_session.expire_all()
    saved = db_session.scalar(select(QARecord).where(QARecord.question == "提交后刷新失败"))
    assert saved is not None


def test_save_feedback_reports_uncertain_after_commit_when_refresh_fails(
    db_session: Session,
    add_user,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    records = QARecordRepository(db_session)
    now = datetime(2026, 8, 4, 12, 0, 0)
    record = records.persist_exchange(
        make_conversation(user.id, "dify-1", now),
        make_record(user.id, "反馈刷新失败", now),
    )
    record.feedback = FeedbackValue.HELPFUL

    def fail_refresh(_instance) -> None:
        raise SQLAlchemyError("secret connection detail")

    monkeypatch.setattr(db_session, "refresh", fail_refresh)

    with pytest.raises(ChatPersistenceUncertainError):
        records.save(record)

    db_session.expire_all()
    saved = db_session.scalar(select(QARecord).where(QARecord.id == record.id))
    assert saved is not None
    assert saved.feedback is FeedbackValue.HELPFUL
