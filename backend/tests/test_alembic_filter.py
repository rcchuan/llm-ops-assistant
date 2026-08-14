from types import SimpleNamespace

from app.db.alembic import include_database_object


def test_preserved_prototype_tables_are_excluded_from_autogenerate() -> None:
    assert include_database_object(
        SimpleNamespace(), "work_orders", "table", True, None
    ) is False
    assert include_database_object(
        SimpleNamespace(table=SimpleNamespace(name="qa_logs")),
        "idx_qa_created",
        "index",
        True,
        None,
    ) is False
    assert include_database_object(
        SimpleNamespace(), "formal_work_orders", "table", True, None
    ) is True
    assert include_database_object(
        SimpleNamespace(), "work_orders", "table", False, None
    ) is True
