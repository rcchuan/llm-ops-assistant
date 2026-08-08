from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class KnowledgeEntryStatus(str, Enum):
    PENDING = "pending"
    SYNC_FAILED = "sync_failed"
    SYNCED = "synced"


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"
    __table_args__ = (
        Index(
            "ix_knowledge_entries_status_created_at_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("formal_work_orders.id"), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    content: Mapped[str] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=False
    )
    status: Mapped[KnowledgeEntryStatus] = mapped_column(
        SqlEnum(
            KnowledgeEntryStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="knowledge_entry_status",
            length=11,
        ),
        nullable=False,
        default=KnowledgeEntryStatus.PENDING,
    )
    dify_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )
