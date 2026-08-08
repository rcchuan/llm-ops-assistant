"""创建候选知识表并移除处理过程列

Revision ID: 20260807_05
Revises: 20260805_04
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260807_05"
down_revision: str | None = "20260805_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


knowledge_entry_status = sa.Enum(
    "pending",
    "sync_failed",
    "synced",
    name="knowledge_entry_status",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "knowledge_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("work_order_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("content", mysql.MEDIUMTEXT(), nullable=False),
        sa.Column("status", knowledge_entry_status, nullable=False),
        sa.Column("dify_document_id", sa.String(length=64), nullable=True),
        sa.Column("sync_error", sa.String(length=500), nullable=True),
        sa.Column("synced_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["work_order_id"], ["formal_work_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id", name="uq_knowledge_entries_work_order_id"
        ),
    )
    op.create_index(
        "ix_knowledge_entries_status_created_at_id",
        "knowledge_entries",
        ["status", "created_at", "id"],
    )
    op.drop_column("formal_work_orders", "processing_notes")


def downgrade() -> None:
    op.add_column(
        "formal_work_orders",
        sa.Column("processing_notes", mysql.MEDIUMTEXT(), nullable=True),
    )
    op.drop_index(
        "ix_knowledge_entries_status_created_at_id",
        table_name="knowledge_entries",
    )
    op.drop_table("knowledge_entries")
