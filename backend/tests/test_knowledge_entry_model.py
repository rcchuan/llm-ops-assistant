from pathlib import Path

from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects import mysql
from sqlalchemy.dialects.mysql import MEDIUMTEXT

from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus


def test_knowledge_entry_table_matches_frozen_contract() -> None:
    assert KnowledgeEntry.__tablename__ == "knowledge_entries"
    assert {status.value for status in KnowledgeEntryStatus} == {
        "pending",
        "sync_failed",
        "synced",
    }

    columns = KnowledgeEntry.__table__.columns
    assert set(columns.keys()) == {
        "id",
        "work_order_id",
        "title",
        "content",
        "status",
        "dify_document_id",
        "sync_error",
        "synced_at",
        "created_at",
        "updated_at",
    }
    assert columns.work_order_id.unique is True
    assert {foreign_key.target_fullname for foreign_key in columns.work_order_id.foreign_keys} == {
        "formal_work_orders.id"
    }
    assert isinstance(columns.content.type.dialect_impl(mysql.dialect()), MEDIUMTEXT)
    assert isinstance(columns.status.type, SqlEnum)
    assert columns.status.type.native_enum is False
    assert {tuple(index.columns.keys()) for index in KnowledgeEntry.__table__.indexes} == {
        ("status", "created_at", "id")
    }


def test_stage_five_migration_only_adds_knowledge_and_drops_processing_notes() -> None:
    migration = Path(
        "alembic/versions/20260807_05_create_knowledge_entries.py"
    ).read_text(encoding="utf-8")
    assert 'revision: str = "20260807_05"' in migration
    assert 'down_revision: str | None = "20260805_04"' in migration
    assert 'op.create_table(\n        "knowledge_entries"' in migration
    assert 'op.drop_column("formal_work_orders", "processing_notes")' in migration
    assert 'op.add_column(\n        "formal_work_orders"' in migration
    assert 'op.drop_table("knowledge_entries")' in migration
    assert 'op.create_table(\n        "work_orders"' not in migration
    assert 'op.alter_column("work_orders"' not in migration
    assert 'op.drop_table("work_orders")' not in migration
    assert "op.bulk_insert" not in migration
    assert "INSERT" not in migration.upper()
