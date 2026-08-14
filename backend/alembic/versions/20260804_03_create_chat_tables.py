"""创建智能问答会话与记录表

Revision ID: 20260804_03
Revises: 20260803_02
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision: str = "20260804_03"
down_revision: str | None = "20260803_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("dify_conversation_id", sa.String(length=64), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_user_id_updated_at",
        "conversations",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "qa_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.String(length=1000), nullable=False),
        sa.Column("answer", mysql.MEDIUMTEXT(), nullable=False),
        sa.Column("dify_message_id", sa.String(length=64), nullable=True),
        sa.Column("retriever_resources", sa.JSON(), nullable=False),
        sa.Column(
            "feedback",
            sa.Enum(
                "helpful",
                "unhelpful",
                name="qa_record_feedback",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=True,
        ),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_qa_records_conversation_id_created_at",
        "qa_records",
        ["conversation_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_qa_records_user_id_created_at",
        "qa_records",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_qa_records_user_id_created_at", table_name="qa_records")
    op.drop_index("ix_qa_records_conversation_id_created_at", table_name="qa_records")
    op.drop_table("qa_records")
    op.drop_index("ix_conversations_user_id_updated_at", table_name="conversations")
    op.drop_table("conversations")
