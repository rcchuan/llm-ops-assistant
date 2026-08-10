from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus
from app.models.qa_record import FeedbackValue, QARecord
from app.models.user import UserRole
from app.models.work_order import WorkOrder, WorkOrderStatus


def auth(client, username: str, password: str = "ValidPass123") -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_statistics_aggregates_existing_tables(client, add_user, db_session) -> None:
    admin = add_user("Admin01", role=UserRole.ADMIN)
    operator = add_user("Operator01", role=UserRole.OPERATOR)
    other_operator = add_user("Operator02", role=UserRole.OPERATOR)
    for index, (user_id, feedback) in enumerate(
        [(operator.id, FeedbackValue.HELPFUL), (operator.id, FeedbackValue.UNHELPFUL), (other_operator.id, None)]
    ):
        record = QARecord(conversation_id=1, user_id=user_id, question=f"q{index}", answer="a", feedback=feedback, response_time_ms=1)
        db_session.add(record)
        db_session.flush()
        if index < 2:
            db_session.add(WorkOrder(qa_record_id=record.id, user_id=user_id, symptom="s", status=[WorkOrderStatus.PENDING, WorkOrderStatus.RESOLVED][index]))
    admin_record = QARecord(conversation_id=1, user_id=admin.id, question="admin q", answer="a", feedback=FeedbackValue.HELPFUL, response_time_ms=1)
    db_session.add(admin_record)
    db_session.flush()
    db_session.add(WorkOrder(qa_record_id=admin_record.id, user_id=admin.id, symptom="s", status=WorkOrderStatus.PROCESSING))
    db_session.commit()
    record = db_session.query(QARecord).filter_by(user_id=other_operator.id).one()
    order = WorkOrder(qa_record_id=record.id, user_id=other_operator.id, symptom="s", status=WorkOrderStatus.CLOSED)
    db_session.add(order)
    db_session.flush()
    db_session.add(KnowledgeEntry(work_order_id=order.id, title="t", content="c", status=KnowledgeEntryStatus.SYNCED))
    db_session.commit()

    response = client.get("/api/v1/admin/statistics/overview", headers=auth(client, admin.username))

    assert response.status_code == 200
    assert response.json() == {
        "qa": {"total_count": 4, "operator_count": 3, "converted_count": 3, "conversion_rate": 100.0},
        "feedback": {"helpful_count": 2, "unhelpful_count": 1, "unrated_count": 1, "satisfaction_rate": 66.67},
        "work_orders": {"pending": 1, "processing": 1, "resolved": 1, "closed": 1},
        "knowledge_entries": {"pending": 0, "sync_failed": 0, "synced": 1},
    }


def test_statistics_requires_auth_and_admin(client, add_user) -> None:
    assert client.get("/api/v1/admin/statistics/overview").status_code == 401
    operator = add_user("Operator01")
    assert client.get("/api/v1/admin/statistics/overview", headers=auth(client, operator.username)).status_code == 403


def test_statistics_empty_database_returns_null_rates_and_fixed_keys(client, add_user) -> None:
    admin = add_user("Admin01", role=UserRole.ADMIN)
    response = client.get("/api/v1/admin/statistics/overview", headers=auth(client, admin.username))
    body = response.json()
    assert body["qa"] == {"total_count": 0, "operator_count": 0, "converted_count": 0, "conversion_rate": None}
    assert body["feedback"] == {"helpful_count": 0, "unhelpful_count": 0, "unrated_count": 0, "satisfaction_rate": None}
    assert body["work_orders"] == {"pending": 0, "processing": 0, "resolved": 0, "closed": 0}
    assert body["knowledge_entries"] == {"pending": 0, "sync_failed": 0, "synced": 0}
