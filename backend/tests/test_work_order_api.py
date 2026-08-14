from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus
from app.models.qa_record import QARecord
from app.models.work_order import WorkOrder, WorkOrderLog, WorkOrderStatus
from app.models.user import UserRole


def auth(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "ValidPass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_qa(db_session: Session, user_id: int, question: str = "数据库连接超时") -> QARecord:
    conversation = Conversation(user_id=user_id, dify_conversation_id=f"dify-{user_id}")
    db_session.add(conversation)
    db_session.flush()
    record = QARecord(
        conversation_id=conversation.id,
        user_id=user_id,
        question=question,
        answer="请检查网络与连接池。",
        dify_message_id=f"message-{user_id}",
        retriever_resources=[],
        response_time_ms=10,
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def create_order(client: TestClient, db_session: Session, user, question: str = "问题") -> tuple[int, dict[str, str]]:
    record = add_qa(db_session, user.id, question)
    user_headers = auth(client, user.username)
    response = client.post(
        "/api/v1/work-orders",
        headers=user_headers,
        json={"qa_record_id": record.id, "symptom": "服务异常"},
    )
    assert response.status_code == 201
    return response.json()["id"], user_headers


def test_operator_creates_work_order_and_creation_log(
    client: TestClient, add_user, db_session: Session
) -> None:
    user = add_user("Operator01")
    record = add_qa(db_session, user.id)

    response = client.post(
        "/api/v1/work-orders",
        headers=auth(client, user.username),
        json={
            "qa_record_id": record.id,
            "symptom": "  应用无法连接数据库  ",
            "attempted_steps": "  已检查 DNS  ",
            "additional_notes": "   ",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["qa_record"]["id"] == record.id
    assert body["symptom"] == "应用无法连接数据库"
    assert body["attempted_steps"] == "已检查 DNS"
    assert body["additional_notes"] is None
    assert body["status"] == "pending"
    order = db_session.scalar(select(WorkOrder).where(WorkOrder.id == body["id"]))
    log = db_session.scalar(select(WorkOrderLog).where(WorkOrderLog.work_order_id == order.id))
    assert order is not None
    assert log is not None
    assert log.from_status is None
    assert log.to_status == WorkOrderStatus.PENDING
    assert log.operator_user_id == user.id


def test_create_validates_length_after_trimming(
    client: TestClient, add_user, db_session: Session
) -> None:
    user = add_user("Operator01")
    record = add_qa(db_session, user.id)

    response = client.post(
        "/api/v1/work-orders",
        headers=auth(client, user.username),
        json={"qa_record_id": record.id, "symptom": f"  {'x' * 2000}  "},
    )

    assert response.status_code == 201
    assert response.json()["symptom"] == "x" * 2000


def test_create_rejects_non_string_fields_as_validation_error(
    client: TestClient, add_user, db_session: Session
) -> None:
    user = add_user("Operator01")
    record = add_qa(db_session, user.id)

    response = client.post(
        "/api/v1/work-orders",
        headers=auth(client, user.username),
        json={"qa_record_id": record.id, "symptom": 123},
    )

    assert response.status_code == 422


def test_create_rejects_admin_other_missing_and_duplicate_questions(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    other = add_user("Operator02")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    record = add_qa(db_session, owner.id)
    payload = {"qa_record_id": record.id, "symptom": "连接失败"}

    assert client.post(
        "/api/v1/work-orders", headers=auth(client, admin.username), json=payload
    ).status_code == 403
    assert client.post(
        "/api/v1/work-orders", headers=auth(client, other.username), json=payload
    ).status_code == 404
    assert client.post(
        "/api/v1/work-orders",
        headers=auth(client, owner.username),
        json={"qa_record_id": 999999, "symptom": "连接失败"},
    ).status_code == 404

    owner_headers = auth(client, owner.username)
    assert client.post("/api/v1/work-orders", headers=owner_headers, json=payload).status_code == 201
    assert client.post("/api/v1/work-orders", headers=owner_headers, json=payload).status_code == 409


def test_owner_and_admin_lists_details_are_isolated_and_paginated(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    other = add_user("Operator02")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    owner_headers = auth(client, owner.username)
    other_headers = auth(client, other.username)
    first_qa = add_qa(db_session, owner.id, "第一个问题")
    second_qa = add_qa(db_session, owner.id, "第二个问题")
    other_qa = add_qa(db_session, other.id, "他人问题")

    first_id = client.post(
        "/api/v1/work-orders",
        headers=owner_headers,
        json={"qa_record_id": first_qa.id, "symptom": "现象一"},
    ).json()["id"]
    second_id = client.post(
        "/api/v1/work-orders",
        headers=owner_headers,
        json={"qa_record_id": second_qa.id, "symptom": "现象二"},
    ).json()["id"]
    other_id = client.post(
        "/api/v1/work-orders",
        headers=other_headers,
        json={"qa_record_id": other_qa.id, "symptom": "他人现象"},
    ).json()["id"]

    owner_page = client.get(
        "/api/v1/work-orders?page=1&page_size=1", headers=owner_headers
    )
    assert owner_page.status_code == 200
    assert owner_page.json()["total"] == 2
    assert owner_page.json()["page"] == 1
    assert owner_page.json()["page_size"] == 1
    assert [item["id"] for item in owner_page.json()["items"]] == [second_id]
    assert client.get(
        f"/api/v1/work-orders/{other_id}", headers=owner_headers
    ).status_code == 404

    admin_page = client.get("/api/v1/work-orders", headers=auth(client, admin.username))
    assert admin_page.status_code == 200
    assert admin_page.json()["total"] == 3
    assert [item["id"] for item in admin_page.json()["items"]] == [
        other_id,
        second_id,
        first_id,
    ]
    assert admin_page.json()["items"][0]["creator"]["username"] == other.username
    assert client.get(
        f"/api/v1/work-orders/{first_id}", headers=auth(client, admin.username)
    ).status_code == 200


def test_links_returns_only_owned_qa_mappings_without_n_plus_one_api_calls(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    other = add_user("Operator02")
    linked = add_qa(db_session, owner.id, "已转单")
    unlinked = add_qa(db_session, owner.id, "未转单")
    foreign = add_qa(db_session, other.id, "他人问答")
    owner_headers = auth(client, owner.username)
    order_id = client.post(
        "/api/v1/work-orders",
        headers=owner_headers,
        json={"qa_record_id": linked.id, "symptom": "连接失败"},
    ).json()["id"]

    response = client.post(
        "/api/v1/work-orders/links",
        headers=owner_headers,
        json={"qa_record_ids": [linked.id, unlinked.id, linked.id, foreign.id, 999999]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {"qa_record_id": linked.id, "work_order_id": order_id},
            {"qa_record_id": unlinked.id, "work_order_id": None},
        ]
    }
    assert client.post(
        "/api/v1/work-orders/links",
        headers=auth(client, other.username),
        json={"qa_record_ids": list(range(1, 52))},
    ).status_code == 422
    admin = add_user("Admin01", role=UserRole.ADMIN)
    assert client.post(
        "/api/v1/work-orders/links",
        headers=auth(client, admin.username),
        json={"qa_record_ids": [linked.id]},
    ).status_code == 403


def test_admin_starts_pending_order_and_writes_log(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)

    assert client.post(
        f"/api/v1/work-orders/{order_id}/start", headers=owner_headers
    ).status_code == 403
    response = client.post(
        f"/api/v1/work-orders/{order_id}/start", headers=auth(client, admin.username)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processing"
    logs = db_session.scalars(
        select(WorkOrderLog)
        .where(WorkOrderLog.work_order_id == order_id)
        .order_by(WorkOrderLog.id)
    ).all()
    assert [(log.from_status, log.to_status) for log in logs] == [
        (None, WorkOrderStatus.PENDING),
        (WorkOrderStatus.PENDING, WorkOrderStatus.PROCESSING),
    ]


def test_admin_saves_processing_content_without_log(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, _ = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    assert client.post(
        f"/api/v1/work-orders/{order_id}/start", headers=admin_headers
    ).status_code == 200

    for payload in (
        {"solution": None},
        {"solution": "  临时方案  "},
    ):
        response = client.put(
            f"/api/v1/work-orders/{order_id}/processing-content",
            headers=admin_headers,
            json=payload,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "processing"
    assert response.json()["solution"] == "临时方案"
    assert len(
        db_session.scalars(
            select(WorkOrderLog).where(WorkOrderLog.work_order_id == order_id)
        ).all()
    ) == 2


def test_resolve_requires_solution_and_writes_status_log(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, _ = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)

    assert client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "   "},
    ).status_code == 409
    response = client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "  调整连接池配置  "},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert response.json()["solution"] == "调整连接池配置"
    logs = db_session.scalars(
        select(WorkOrderLog)
        .where(WorkOrderLog.work_order_id == order_id)
        .order_by(WorkOrderLog.id)
    ).all()
    assert logs[-1].from_status == WorkOrderStatus.PROCESSING
    assert logs[-1].to_status == WorkOrderStatus.RESOLVED


def test_owner_confirms_resolved_order_and_closed_is_read_only(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    other = add_user("Operator02")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)
    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "修复配置"},
    )

    assert client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=admin_headers
    ).status_code == 403
    assert client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=auth(client, other.username)
    ).status_code == 404
    response = client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=owner_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    entry = db_session.scalar(
        select(KnowledgeEntry).where(KnowledgeEntry.work_order_id == order_id)
    )
    assert entry is not None
    assert entry.status == KnowledgeEntryStatus.PENDING
    assert entry.title == "问题"
    assert entry.content == "## 故障现象\n服务异常\n\n## 解决方案\n修复配置"
    assert client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=owner_headers
    ).status_code == 409
    last_log = db_session.scalars(
        select(WorkOrderLog)
        .where(WorkOrderLog.work_order_id == order_id)
        .order_by(WorkOrderLog.id.desc())
    ).first()
    assert last_log.from_status == WorkOrderStatus.RESOLVED
    assert last_log.to_status == WorkOrderStatus.CLOSED


def test_reopen_keeps_latest_note_on_order_and_all_notes_in_logs(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)
    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "第一次方案"},
    )

    assert client.post(
        f"/api/v1/work-orders/{order_id}/reopen",
        headers=owner_headers,
        json={"unresolved_note": "   "},
    ).status_code == 409
    first = client.post(
        f"/api/v1/work-orders/{order_id}/reopen",
        headers=owner_headers,
        json={"unresolved_note": "  仍然超时  "},
    )
    assert first.status_code == 200
    assert first.json()["status"] == "processing"
    assert first.json()["unresolved_note"] == "仍然超时"
    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "第二次方案"},
    )
    second = client.post(
        f"/api/v1/work-orders/{order_id}/reopen",
        headers=owner_headers,
        json={"unresolved_note": "偶尔复现"},
    )
    assert second.status_code == 200
    assert second.json()["unresolved_note"] == "偶尔复现"
    reopen_logs = db_session.scalars(
        select(WorkOrderLog)
        .where(
            WorkOrderLog.work_order_id == order_id,
            WorkOrderLog.to_status == WorkOrderStatus.PROCESSING,
            WorkOrderLog.from_status == WorkOrderStatus.RESOLVED,
        )
        .order_by(WorkOrderLog.id)
    ).all()
    assert [log.note for log in reopen_logs] == ["仍然超时", "偶尔复现"]


def test_illegal_state_and_role_matrix_is_rejected(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)

    assert client.put(
        f"/api/v1/work-orders/{order_id}/processing-content",
        headers=admin_headers,
        json={"solution": "越级"},
    ).status_code == 409
    assert client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "越级"},
    ).status_code == 409
    assert client.post(
        f"/api/v1/work-orders/{order_id}/reopen",
        headers=admin_headers,
        json={"unresolved_note": "角色错误"},
    ).status_code == 403
    assert client.put(
        f"/api/v1/work-orders/{order_id}/processing-content",
        headers=owner_headers,
        json={"solution": "角色错误"},
    ).status_code == 403


def test_processing_draft_visibility_tracks_status(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)
    client.put(
        f"/api/v1/work-orders/{order_id}/processing-content",
        headers=admin_headers,
        json={"solution": "草稿方案"},
    )

    owner_processing = client.get(
        f"/api/v1/work-orders/{order_id}", headers=owner_headers
    ).json()
    admin_processing = client.get(
        f"/api/v1/work-orders/{order_id}", headers=admin_headers
    ).json()
    assert owner_processing["solution"] is None
    assert admin_processing["solution"] == "草稿方案"

    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "正式方案"},
    )
    owner_resolved = client.get(
        f"/api/v1/work-orders/{order_id}", headers=owner_headers
    ).json()
    assert owner_resolved["solution"] == "正式方案"

    client.post(
        f"/api/v1/work-orders/{order_id}/reopen",
        headers=owner_headers,
        json={"unresolved_note": "仍未恢复"},
    )
    owner_reopened = client.get(
        f"/api/v1/work-orders/{order_id}", headers=owner_headers
    ).json()
    assert owner_reopened["solution"] is None


def test_processing_endpoints_reject_removed_processing_notes(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, _ = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)

    assert client.put(
        f"/api/v1/work-orders/{order_id}/processing-content",
        headers=admin_headers,
        json={"processing_notes": "旧字段", "solution": "方案"},
    ).status_code == 422
    assert client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"processing_notes": "旧字段", "solution": "方案"},
    ).status_code == 422


def test_confirm_rolls_back_closed_log_and_candidate_when_commit_fails(
    client: TestClient, add_user, db_session: Session, monkeypatch
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)
    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "修复配置"},
    )
    original_commit = db_session.commit
    monkeypatch.setattr(
        db_session,
        "commit",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("commit failed")),
    )

    response = client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=owner_headers
    )
    monkeypatch.setattr(db_session, "commit", original_commit)
    db_session.expire_all()

    assert response.status_code == 503
    assert response.json()["detail"] == "确认失败，请稍后重试"
    assert db_session.get(WorkOrder, order_id).status == WorkOrderStatus.RESOLVED
    assert db_session.scalar(
        select(KnowledgeEntry).where(KnowledgeEntry.work_order_id == order_id)
    ) is None
    logs = db_session.scalars(
        select(WorkOrderLog).where(WorkOrderLog.work_order_id == order_id)
    ).all()
    assert all(log.to_status != WorkOrderStatus.CLOSED for log in logs)


def test_confirm_rejects_existing_candidate_without_creating_duplicate(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    order_id, owner_headers = create_order(client, db_session, owner)
    admin_headers = auth(client, admin.username)
    client.post(f"/api/v1/work-orders/{order_id}/start", headers=admin_headers)
    client.post(
        f"/api/v1/work-orders/{order_id}/resolve",
        headers=admin_headers,
        json={"solution": "修复配置"},
    )
    db_session.add(
        KnowledgeEntry(
            work_order_id=order_id,
            title="已有候选",
            content="正文",
            status=KnowledgeEntryStatus.PENDING,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/work-orders/{order_id}/confirm", headers=owner_headers
    )

    assert response.status_code == 409
    assert db_session.get(WorkOrder, order_id).status == WorkOrderStatus.RESOLVED
    assert len(
        db_session.scalars(
            select(KnowledgeEntry).where(KnowledgeEntry.work_order_id == order_id)
        ).all()
    ) == 1
