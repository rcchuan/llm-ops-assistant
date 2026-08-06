from unittest.mock import Mock

from app.models.qa_record import QARecord
from app.models.user import User, UserRole
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.repositories.work_order_repository import WorkOrderBundle, WorkOrderRepository
from app.services.work_order_service import WorkOrderService


def test_start_locks_order_before_checking_and_changing_status() -> None:
    repository = Mock(spec=WorkOrderRepository)
    admin = User(id=1, username="admin", display_name="管理员", role=UserRole.ADMIN)
    order = WorkOrder(id=1, qa_record_id=1, user_id=2, symptom="连接失败")
    order.status = WorkOrderStatus.PENDING
    repository.get_bundle.return_value = WorkOrderBundle(
        order=order,
        record=QARecord(id=1, user_id=2, conversation_id=1, question="问题", answer="回答"),
        creator=User(id=2, username="owner", display_name="运维员", role=UserRole.OPERATOR),
    )

    WorkOrderService(repository).start(admin, order.id)

    repository.get_bundle.assert_called_once_with(order.id, for_update=True)


def test_present_applies_role_and_status_visibility() -> None:
    repository = Mock(spec=WorkOrderRepository)
    service = WorkOrderService(repository)
    owner = User(id=2, username="owner", display_name="运维员", role=UserRole.OPERATOR)
    admin = User(id=1, username="admin", display_name="管理员", role=UserRole.ADMIN)
    order = WorkOrder(
        id=1,
        qa_record_id=1,
        user_id=owner.id,
        symptom="连接失败",
        processing_notes="内部排查",
        solution="草稿方案",
        status=WorkOrderStatus.PROCESSING,
    )
    bundle = WorkOrderBundle(
        order=order,
        record=QARecord(id=1, user_id=owner.id, conversation_id=1, question="问题", answer="回答"),
        creator=owner,
    )

    owner_view = service.present(owner, bundle)
    admin_view = service.present(admin, bundle)

    assert owner_view.processing_notes is None
    assert owner_view.solution is None
    assert owner_view.creator is None
    assert admin_view.processing_notes == "内部排查"
    assert admin_view.solution == "草稿方案"
    assert admin_view.creator is owner
