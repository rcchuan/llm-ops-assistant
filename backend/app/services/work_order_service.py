from dataclasses import dataclass

from app.core.exceptions import (
    WorkOrderAlreadyExistsError,
    WorkOrderConflictError,
    WorkOrderForbiddenError,
    WorkOrderNotFoundError,
)
from app.models.qa_record import QARecord
from app.models.user import User, UserRole
from app.models.work_order import WorkOrder, WorkOrderLog, WorkOrderStatus
from app.repositories.work_order_repository import WorkOrderBundle, WorkOrderRepository


@dataclass(frozen=True, slots=True)
class WorkOrderView:
    order: WorkOrder
    record: QARecord
    creator: User | None
    processing_notes: str | None
    solution: str | None


class WorkOrderService:
    def __init__(self, repository: WorkOrderRepository):
        self.repository = repository

    def present(self, user: User, bundle: WorkOrderBundle) -> WorkOrderView:
        can_view_processing = user.role == UserRole.ADMIN or bundle.order.status in {
            WorkOrderStatus.RESOLVED,
            WorkOrderStatus.CLOSED,
        }
        return WorkOrderView(
            order=bundle.order,
            record=bundle.record,
            creator=bundle.creator if user.role == UserRole.ADMIN else None,
            processing_notes=(
                bundle.order.processing_notes if can_view_processing else None
            ),
            solution=bundle.order.solution if can_view_processing else None,
        )

    def create(
        self,
        user: User,
        *,
        qa_record_id: int,
        symptom: str,
        attempted_steps: str | None,
        additional_notes: str | None,
    ) -> tuple[WorkOrder, QARecord]:
        if user.role != UserRole.OPERATOR:
            raise WorkOrderForbiddenError
        record = self.repository.get_qa_record(qa_record_id)
        if record is None or record.user_id != user.id:
            raise WorkOrderNotFoundError
        if self.repository.get_by_qa_record_id(qa_record_id) is not None:
            raise WorkOrderAlreadyExistsError
        order = WorkOrder(
            qa_record_id=record.id,
            user_id=user.id,
            symptom=symptom,
            attempted_steps=attempted_steps,
            additional_notes=additional_notes,
            status=WorkOrderStatus.PENDING,
        )
        log = WorkOrderLog(
            work_order_id=0,
            from_status=None,
            to_status=WorkOrderStatus.PENDING,
            operator_user_id=user.id,
        )
        return self.repository.create(order, log), record

    def list_orders(
        self, user: User, *, page: int, page_size: int
    ) -> tuple[list[WorkOrderBundle], int]:
        owner_id = None if user.role == UserRole.ADMIN else user.id
        return self.repository.list_orders(page=page, page_size=page_size, owner_id=owner_id)

    def get(self, user: User, order_id: int) -> WorkOrderBundle:
        bundle = self.repository.get_bundle(order_id)
        if bundle is None or (
            user.role != UserRole.ADMIN and bundle.order.user_id != user.id
        ):
            raise WorkOrderNotFoundError
        return bundle

    def get_links(self, user: User, qa_record_ids: list[int]) -> list[tuple[int, int | None]]:
        if user.role != UserRole.OPERATOR:
            raise WorkOrderForbiddenError
        links = self.repository.get_links(user.id, qa_record_ids)
        return [(qa_id, links[qa_id]) for qa_id in qa_record_ids if qa_id in links]

    def start(self, user: User, order_id: int) -> WorkOrderBundle:
        if user.role != UserRole.ADMIN:
            raise WorkOrderForbiddenError
        bundle = self.repository.get_bundle(order_id, for_update=True)
        if bundle is None:
            raise WorkOrderNotFoundError
        if bundle.order.status != WorkOrderStatus.PENDING:
            raise WorkOrderConflictError
        previous = bundle.order.status
        bundle.order.status = WorkOrderStatus.PROCESSING
        self.repository.save_transition(
            bundle.order,
            from_status=previous,
            operator_user_id=user.id,
        )
        return bundle

    def save_processing_content(
        self,
        user: User,
        order_id: int,
        *,
        processing_notes: str | None,
        solution: str | None,
    ) -> WorkOrderBundle:
        if user.role != UserRole.ADMIN:
            raise WorkOrderForbiddenError
        bundle = self.repository.get_bundle(order_id, for_update=True)
        if bundle is None:
            raise WorkOrderNotFoundError
        if bundle.order.status != WorkOrderStatus.PROCESSING:
            raise WorkOrderConflictError
        bundle.order.processing_notes = processing_notes
        bundle.order.solution = solution
        self.repository.save_content(bundle.order)
        return bundle

    def resolve(
        self,
        user: User,
        order_id: int,
        *,
        processing_notes: str | None,
        solution: str,
    ) -> WorkOrderBundle:
        if user.role != UserRole.ADMIN:
            raise WorkOrderForbiddenError
        bundle = self.repository.get_bundle(order_id, for_update=True)
        if bundle is None:
            raise WorkOrderNotFoundError
        if bundle.order.status != WorkOrderStatus.PROCESSING or not solution.strip():
            raise WorkOrderConflictError
        previous = bundle.order.status
        bundle.order.processing_notes = processing_notes
        bundle.order.solution = solution.strip()
        bundle.order.status = WorkOrderStatus.RESOLVED
        self.repository.save_transition(
            bundle.order,
            from_status=previous,
            operator_user_id=user.id,
        )
        return bundle

    def confirm(self, user: User, order_id: int) -> WorkOrderBundle:
        if user.role != UserRole.OPERATOR:
            raise WorkOrderForbiddenError
        bundle = self.repository.get_bundle(order_id, for_update=True)
        if bundle is None or bundle.order.user_id != user.id:
            raise WorkOrderNotFoundError
        if bundle.order.status != WorkOrderStatus.RESOLVED:
            raise WorkOrderConflictError
        previous = bundle.order.status
        bundle.order.status = WorkOrderStatus.CLOSED
        self.repository.save_transition(
            bundle.order,
            from_status=previous,
            operator_user_id=user.id,
        )
        return bundle

    def reopen(
        self, user: User, order_id: int, *, unresolved_note: str
    ) -> WorkOrderBundle:
        if user.role != UserRole.OPERATOR:
            raise WorkOrderForbiddenError
        bundle = self.repository.get_bundle(order_id, for_update=True)
        if bundle is None or bundle.order.user_id != user.id:
            raise WorkOrderNotFoundError
        note = unresolved_note.strip()
        if bundle.order.status != WorkOrderStatus.RESOLVED or not note:
            raise WorkOrderConflictError
        previous = bundle.order.status
        bundle.order.unresolved_note = note
        bundle.order.status = WorkOrderStatus.PROCESSING
        self.repository.save_transition(
            bundle.order,
            from_status=previous,
            operator_user_id=user.id,
            note=note,
        )
        return bundle
