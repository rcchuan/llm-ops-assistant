from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class FeedbackValue(str, Enum):
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"


class QARecord(Base):
    __tablename__ = "qa_records"
    __table_args__ = (
        Index(
            "ix_qa_records_conversation_id_created_at",
            "conversation_id",
            "created_at",
        ),
        Index("ix_qa_records_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    question: Mapped[str] = mapped_column(String(1000), nullable=False)
    answer: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"),
        nullable=False,
    )
    dify_message_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retriever_resources: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    feedback: Mapped[FeedbackValue | None] = mapped_column(
        SqlEnum(
            FeedbackValue,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="qa_record_feedback",
            length=9,
        ),
        nullable=True,
    )
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
