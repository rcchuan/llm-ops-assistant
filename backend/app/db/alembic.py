from typing import Any


PRESERVED_PROTOTYPE_TABLES = {
    "work_orders",
    "qa_logs",
    "corpus_raw",
    "corpus_clean",
    "high_freq_issues",
}


def include_database_object(
    object_: Any,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: Any,
) -> bool:
    if not reflected or compare_to is not None:
        return True
    table_name = (
        name
        if type_ == "table"
        else getattr(getattr(object_, "table", None), "name", None)
    )
    return table_name not in PRESERVED_PROTOTYPE_TABLES
