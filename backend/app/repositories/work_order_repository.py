from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import WorkOrderAlreadyExistsError, WorkOrderPersistenceError
from app.models.knowledge_entry import KnowledgeEntry
from app.models.qa_record import QARecord
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderLog, WorkOrderStatus


@dataclass(frozen=True, slots=True)
class WorkOrderBundle:
    order: WorkOrder
    record: QARecord
    creator: User


class WorkOrderRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_qa_record(self, qa_record_id: int) -> QARecord | None:
        try:
            return self.session.get(QARecord, qa_record_id)
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None

    def get_by_qa_record_id(self, qa_record_id: int) -> WorkOrder | None:
        try:
            return self.session.scalar(
                select(WorkOrder).where(WorkOrder.qa_record_id == qa_record_id)
            )
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None

    def list_orders(
        self, *, page: int, page_size: int, owner_id: int | None
    ) -> tuple[list[WorkOrderBundle], int]:
        condition = WorkOrder.user_id == owner_id if owner_id is not None else None
        statement = (
            select(WorkOrder, QARecord, User)
            .join(QARecord, QARecord.id == WorkOrder.qa_record_id)
            .join(User, User.id == WorkOrder.user_id)
        )
        count_statement = select(func.count()).select_from(WorkOrder)
        if condition is not None:
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        try:
            rows = self.session.execute(
                statement.order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return (
                [WorkOrderBundle(order=row[0], record=row[1], creator=row[2]) for row in rows],
                self.session.scalar(count_statement) or 0,
            )
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None

    def get_bundle(
        self, order_id: int, *, for_update: bool = False
    ) -> WorkOrderBundle | None:
        statement = (
            select(WorkOrder, QARecord, User)
            .join(QARecord, QARecord.id == WorkOrder.qa_record_id)
            .join(User, User.id == WorkOrder.user_id)
            .where(WorkOrder.id == order_id)
        )
        if for_update:
            statement = statement.with_for_update()
        try:
            row = self.session.execute(statement).one_or_none()
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None
        if row is None:
            return None
        return WorkOrderBundle(order=row[0], record=row[1], creator=row[2])

    def get_links(self, user_id: int, qa_record_ids: list[int]) -> dict[int, int | None]:
        try:
            rows = self.session.execute(
                select(QARecord.id, WorkOrder.id)
                .outerjoin(WorkOrder, WorkOrder.qa_record_id == QARecord.id)
                .where(QARecord.user_id == user_id, QARecord.id.in_(qa_record_ids))
            ).all()
            return {row[0]: row[1] for row in rows}
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None

    def get_knowledge_entry(self, work_order_id: int) -> KnowledgeEntry | None:
        try:
            return self.session.scalar(
                select(KnowledgeEntry).where(
                    KnowledgeEntry.work_order_id == work_order_id
                )
            )
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None

    def create(self, order: WorkOrder, log: WorkOrderLog) -> WorkOrder:
        try:
            self.session.add(order)
            self.session.flush()
            log.work_order_id = order.id
            self.session.add(log)
            self.session.commit()
        except IntegrityError as error:
            self.session.rollback()
            if self._is_qa_record_unique_conflict(error):
                raise WorkOrderAlreadyExistsError from None
            raise WorkOrderPersistenceError from None
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None
        return order

    def save_transition(
        self,
        order: WorkOrder,
        *,
        from_status: WorkOrderStatus,
        operator_user_id: int,
        note: str | None = None,
    ) -> WorkOrder:
        log = WorkOrderLog(
            work_order_id=order.id,
            from_status=from_status,
            to_status=order.status,
            operator_user_id=operator_user_id,
            note=note,
        )
        try:
            self.session.add(log)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None
        return order

    def close_with_knowledge(
        self,
        order: WorkOrder,
        entry: KnowledgeEntry,
        *,
        from_status: WorkOrderStatus,
        operator_user_id: int,
    ) -> WorkOrder:
        log = WorkOrderLog(
            work_order_id=order.id,
            from_status=from_status,
            to_status=order.status,
            operator_user_id=operator_user_id,
        )
        try:
            self.session.add(log)
            self.session.add(entry)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None
        return order

    def save_content(self, order: WorkOrder) -> WorkOrder:
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise WorkOrderPersistenceError from None
        return order

    @staticmethod
    def _is_qa_record_unique_conflict(error: IntegrityError) -> bool:
        arguments = getattr(error.orig, "args", ())
        mysql_duplicate = (
            len(arguments) >= 2
            and arguments[0] == 1062
            and "uq_formal_work_orders_qa_record_id" in str(arguments[1])
        )
        sqlite_duplicate = (
            "UNIQUE constraint failed: formal_work_orders.qa_record_id"
            in str(error.orig)
        )
        return mysql_duplicate or sqlite_duplicate
