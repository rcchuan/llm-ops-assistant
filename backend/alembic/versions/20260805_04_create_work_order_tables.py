"""创建工单与工单状态日志表

Revision ID: 20260805_04
Revises: 20260804_03
Create Date: 2026-08-05
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260805_04"
down_revision: str | None = "20260804_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


work_order_status = sa.Enum(
    "pending",
    "processing",
    "resolved",
    "closed",
    name="work_order_status",
    native_enum=False,
    create_constraint=True,
)
log_from_status = sa.Enum(
    "pending", "processing", "resolved", "closed",
    name="work_order_log_from_status", native_enum=False, create_constraint=True,
)
log_to_status = sa.Enum(
    "pending", "processing", "resolved", "closed",
    name="work_order_log_to_status", native_enum=False, create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "formal_work_orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("qa_record_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symptom", sa.Text(), nullable=False),
        sa.Column("attempted_steps", sa.Text(), nullable=True),
        sa.Column("additional_notes", sa.Text(), nullable=True),
        sa.Column("processing_notes", mysql.MEDIUMTEXT(), nullable=True),
        sa.Column("solution", mysql.MEDIUMTEXT(), nullable=True),
        sa.Column("unresolved_note", sa.Text(), nullable=True),
        sa.Column("status", work_order_status, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["qa_record_id"], ["qa_records.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "qa_record_id", name="uq_formal_work_orders_qa_record_id"
        ),
    )
    op.create_index(
        "ix_formal_work_orders_user_id_created_at",
        "formal_work_orders",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_formal_work_orders_created_at",
        "formal_work_orders",
        ["created_at"],
    )
    op.create_table(
        "formal_work_order_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("from_status", log_from_status, nullable=True),
        sa.Column("to_status", log_to_status, nullable=False),
        sa.Column("operator_user_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["work_order_id"], ["formal_work_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_formal_work_order_logs_work_order_id_created_at",
        "formal_work_order_logs",
        ["work_order_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_formal_work_order_logs_work_order_id_created_at",
        table_name="formal_work_order_logs",
    )
    op.drop_table("formal_work_order_logs")
    op.drop_index(
        "ix_formal_work_orders_created_at", table_name="formal_work_orders"
    )
    op.drop_index(
        "ix_formal_work_orders_user_id_created_at",
        table_name="formal_work_orders",
    )
    op.drop_table("formal_work_orders")
