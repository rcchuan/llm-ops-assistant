from pathlib import Path

from sqlalchemy import Enum as SqlEnum

from app.models.work_order import WorkOrder, WorkOrderLog, WorkOrderStatus


def test_work_order_tables_match_stage_four_contract() -> None:
    assert WorkOrder.__tablename__ == "formal_work_orders"
    assert WorkOrderLog.__tablename__ == "formal_work_order_logs"
    assert {status.value for status in WorkOrderStatus} == {
        "pending",
        "processing",
        "resolved",
        "closed",
    }

    columns = WorkOrder.__table__.columns
    assert set(columns.keys()) == {
        "id",
        "qa_record_id",
        "user_id",
        "symptom",
        "attempted_steps",
        "additional_notes",
        "processing_notes",
        "solution",
        "unresolved_note",
        "status",
        "created_at",
        "updated_at",
    }
    assert columns.qa_record_id.unique is True
    assert isinstance(columns.status.type, SqlEnum)
    assert columns.status.type.native_enum is False

    work_order_indexes = {tuple(index.columns.keys()) for index in WorkOrder.__table__.indexes}
    log_indexes = {tuple(index.columns.keys()) for index in WorkOrderLog.__table__.indexes}
    assert ("user_id", "created_at") in work_order_indexes
    assert ("created_at",) in work_order_indexes
    assert ("work_order_id", "created_at") in log_indexes


def test_stage_four_migration_only_owns_work_order_tables() -> None:
    migration = Path("alembic/versions/20260805_04_create_work_order_tables.py").read_text(
        encoding="utf-8"
    )
    assert 'down_revision: str | None = "20260804_03"' in migration
    assert 'op.create_table(\n        "formal_work_orders"' in migration
    assert 'op.create_table(\n        "formal_work_order_logs"' in migration
    assert '["formal_work_orders.id"]' in migration
    assert 'op.drop_table("formal_work_order_logs")' in migration
    assert 'op.drop_table("formal_work_orders")' in migration
    assert 'op.create_table(\n        "work_orders"' not in migration
    assert 'op.alter_column("work_orders"' not in migration
    assert 'op.drop_table("work_orders")' not in migration
    assert "qa_records" not in migration.split("def downgrade()", maxsplit=1)[1]
    assert "conversations" not in migration.split("def downgrade()", maxsplit=1)[1]
    assert "users" not in migration.split("def downgrade()", maxsplit=1)[1]
