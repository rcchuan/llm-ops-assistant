import sqlite3
from unittest.mock import Mock

import pytest
from pymysql.err import IntegrityError as PyMySQLIntegrityError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import WorkOrderAlreadyExistsError, WorkOrderPersistenceError
from app.models.work_order import WorkOrder, WorkOrderLog, WorkOrderStatus
from app.repositories.work_order_repository import WorkOrderRepository


def make_order_and_log() -> tuple[WorkOrder, WorkOrderLog]:
    order = WorkOrder(qa_record_id=1, user_id=1, symptom="连接失败")
    log = WorkOrderLog(
        work_order_id=0,
        from_status=None,
        to_status=WorkOrderStatus.PENDING,
        operator_user_id=1,
    )
    return order, log


@pytest.mark.parametrize(
    "original_error",
    [
        PyMySQLIntegrityError(
            1062,
            "Duplicate entry '1' for key 'uq_formal_work_orders_qa_record_id'",
        ),
        sqlite3.IntegrityError(
            "UNIQUE constraint failed: formal_work_orders.qa_record_id"
        ),
    ],
)
def test_create_converts_qa_record_unique_conflict_and_rolls_back(
    original_error: Exception,
) -> None:
    session = Mock()
    session.flush.side_effect = IntegrityError("insert", {}, original_error)
    repository = WorkOrderRepository(session)
    order, log = make_order_and_log()

    with pytest.raises(WorkOrderAlreadyExistsError):
        repository.create(order, log)

    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "original_error",
    [
        PyMySQLIntegrityError(1048, "Column 'qa_record_id' cannot be null"),
        PyMySQLIntegrityError(
            1452,
            "Cannot add or update a child row: a foreign key constraint fails",
        ),
        PyMySQLIntegrityError(
            9999,
            "uq_formal_work_orders_qa_record_id is mentioned but is not duplicate",
        ),
    ],
)
def test_create_does_not_report_other_integrity_failures_as_duplicate(
    original_error: Exception,
) -> None:
    session = Mock()
    session.flush.side_effect = IntegrityError("insert", {}, original_error)
    repository = WorkOrderRepository(session)
    order, log = make_order_and_log()

    with pytest.raises(WorkOrderPersistenceError):
        repository.create(order, log)

    session.rollback.assert_called_once_with()


def test_create_commit_failure_rolls_back() -> None:
    session = Mock()
    session.commit.side_effect = SQLAlchemyError("commit failed")
    repository = WorkOrderRepository(session)
    order, log = make_order_and_log()

    with pytest.raises(WorkOrderPersistenceError):
        repository.create(order, log)

    session.rollback.assert_called_once_with()
    session.refresh.assert_not_called()


def test_create_commit_success_does_not_depend_on_refresh() -> None:
    session = Mock()
    session.refresh.side_effect = SQLAlchemyError("refresh failed")
    repository = WorkOrderRepository(session)
    order, log = make_order_and_log()

    assert repository.create(order, log) is order

    session.commit.assert_called_once_with()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


def test_save_transition_commit_success_does_not_depend_on_refresh() -> None:
    session = Mock()
    session.refresh.side_effect = SQLAlchemyError("refresh failed")
    repository = WorkOrderRepository(session)
    order, _ = make_order_and_log()
    order.id = 1
    order.status = WorkOrderStatus.PROCESSING

    assert repository.save_transition(
        order,
        from_status=WorkOrderStatus.PENDING,
        operator_user_id=2,
    ) is order

    session.commit.assert_called_once_with()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


def test_save_transition_commit_failure_rolls_back() -> None:
    session = Mock()
    session.commit.side_effect = SQLAlchemyError("commit failed")
    repository = WorkOrderRepository(session)
    order, _ = make_order_and_log()
    order.id = 1
    order.status = WorkOrderStatus.PROCESSING

    with pytest.raises(WorkOrderPersistenceError):
        repository.save_transition(
            order,
            from_status=WorkOrderStatus.PENDING,
            operator_user_id=2,
        )

    session.rollback.assert_called_once_with()
    session.refresh.assert_not_called()


def test_save_content_commit_success_does_not_depend_on_refresh() -> None:
    session = Mock()
    session.refresh.side_effect = SQLAlchemyError("refresh failed")
    repository = WorkOrderRepository(session)
    order, _ = make_order_and_log()

    assert repository.save_content(order) is order

    session.commit.assert_called_once_with()
    session.refresh.assert_not_called()
    session.rollback.assert_not_called()


def test_save_content_commit_failure_rolls_back() -> None:
    session = Mock()
    session.commit.side_effect = SQLAlchemyError("commit failed")
    repository = WorkOrderRepository(session)
    order, _ = make_order_and_log()

    with pytest.raises(WorkOrderPersistenceError):
        repository.save_content(order)

    session.rollback.assert_called_once_with()
    session.refresh.assert_not_called()


def test_get_bundle_converts_query_failure_and_rolls_back() -> None:
    session = Mock()
    session.execute.side_effect = SQLAlchemyError("query failed")
    repository = WorkOrderRepository(session)

    with pytest.raises(WorkOrderPersistenceError):
        repository.get_bundle(1)

    session.rollback.assert_called_once_with()


def test_get_bundle_can_lock_the_order_for_state_changes() -> None:
    session = Mock()
    session.execute.return_value.one_or_none.return_value = None
    repository = WorkOrderRepository(session)

    repository.get_bundle(1, for_update=True)

    statement = session.execute.call_args.args[0]
    assert "FOR UPDATE" in str(statement)
