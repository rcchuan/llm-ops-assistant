from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import ChatPersistenceError, ChatPersistenceUncertainError
from app.models.conversation import Conversation
from app.models.qa_record import QARecord


class QARecordRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_by_conversation(
        self,
        conversation_id: int,
        user_id: int,
        *,
        limit: int = 50,
    ) -> list[QARecord]:
        records = self.session.scalars(
            select(QARecord)
            .where(
                QARecord.conversation_id == conversation_id,
                QARecord.user_id == user_id,
            )
            .order_by(QARecord.created_at.desc(), QARecord.id.desc())
            .limit(limit)
        ).all()
        return list(reversed(records))

    def list_recent_by_user(self, user_id: int, *, limit: int = 50) -> list[QARecord]:
        return list(
            self.session.scalars(
                select(QARecord)
                .where(QARecord.user_id == user_id)
                .order_by(QARecord.created_at.desc(), QARecord.id.desc())
                .limit(limit)
            ).all()
        )

    def get_owned_by_id(self, record_id: int, user_id: int) -> QARecord | None:
        return self.session.scalar(
            select(QARecord).where(
                QARecord.id == record_id,
                QARecord.user_id == user_id,
            )
        )

    def persist_exchange(
        self,
        conversation: Conversation,
        record: QARecord,
    ) -> QARecord:
        try:
            self.session.add(conversation)
            self.session.flush()
            record.conversation_id = conversation.id
            self.session.add(record)
            self.session.commit()
        except SQLAlchemyError:
            self._rollback_quietly()
            raise ChatPersistenceError("问答记录保存失败") from None
        try:
            self.session.refresh(conversation)
            self.session.refresh(record)
        except SQLAlchemyError:
            raise ChatPersistenceUncertainError("问答记录保存状态无法确认") from None
        return record

    def save(self, record: QARecord) -> QARecord:
        try:
            self.session.commit()
        except SQLAlchemyError:
            self._rollback_quietly()
            raise ChatPersistenceError("问答记录保存失败") from None
        try:
            self.session.refresh(record)
        except SQLAlchemyError:
            raise ChatPersistenceUncertainError("反馈保存状态无法确认") from None
        return record

    def _rollback_quietly(self) -> None:
        try:
            self.session.rollback()
        except SQLAlchemyError:
            pass
