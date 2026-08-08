from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import KnowledgeEntryPersistenceError
from app.models.knowledge_entry import KnowledgeEntry
from app.repositories.knowledge_repository import KnowledgeRepository


def test_get_can_lock_entry_for_edit_and_sync() -> None:
    session = Mock()
    session.scalar.return_value = None
    repository = KnowledgeRepository(session)

    repository.get(7, for_update=True)

    statement = session.scalar.call_args.args[0]
    assert "FOR UPDATE" in str(statement)


def test_list_query_failure_rolls_back() -> None:
    session = Mock()
    session.scalars.side_effect = SQLAlchemyError("query failed")
    repository = KnowledgeRepository(session)

    with pytest.raises(KnowledgeEntryPersistenceError):
        repository.list_entries(page=1, page_size=20)

    session.rollback.assert_called_once_with()


def test_save_failure_rolls_back() -> None:
    session = Mock()
    session.commit.side_effect = SQLAlchemyError("commit failed")
    repository = KnowledgeRepository(session)

    with pytest.raises(KnowledgeEntryPersistenceError):
        repository.save(KnowledgeEntry())

    session.rollback.assert_called_once_with()
