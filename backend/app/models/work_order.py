from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class WorkOrderStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RESOLVED = "resolved"
    CLOSED = "closed"


def status_column(name: str) -> SqlEnum:
    return SqlEnum(
        WorkOrderStatus,
        values_callable=lambda values: [value.value for value in values],
        native_enum=False,
        create_constraint=True,
        name=name,
        length=10,
    )


class WorkOrder(Base):
    __tablename__ = "formal_work_orders"
    __table_args__ = (
        Index("ix_formal_work_orders_user_id_created_at", "user_id", "created_at"),
        Index("ix_formal_work_orders_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qa_record_id: Mapped[int] = mapped_column(
        ForeignKey("qa_records.id"), nullable=False, unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    symptom: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_steps: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_notes: Mapped[str | None] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=True
    )
    solution: Mapped[str | None] = mapped_column(
        Text().with_variant(MEDIUMTEXT(), "mysql"), nullable=True
    )
    unresolved_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WorkOrderStatus] = mapped_column(
        status_column("work_order_status"), nullable=False, default=WorkOrderStatus.PENDING
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now, onupdate=utc_now
    )


class WorkOrderLog(Base):
    __tablename__ = "formal_work_order_logs"
    __table_args__ = (
        Index(
            "ix_formal_work_order_logs_work_order_id_created_at",
            "work_order_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(
        ForeignKey("formal_work_orders.id"), nullable=False
    )
    from_status: Mapped[WorkOrderStatus | None] = mapped_column(
        status_column("work_order_log_from_status"), nullable=True
    )
    to_status: Mapped[WorkOrderStatus] = mapped_column(
        status_column("work_order_log_to_status"), nullable=False
    )
    operator_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
