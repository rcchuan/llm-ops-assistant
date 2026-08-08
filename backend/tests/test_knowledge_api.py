from datetime import datetime, timedelta
import json

import httpx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_dify_dataset_client
from app.core.config import Settings
from app.integrations.dify.dataset_client import DifyDatasetClient
from app.main import app
from app.models.conversation import Conversation
from app.models.knowledge_entry import KnowledgeEntry, KnowledgeEntryStatus
from app.models.qa_record import QARecord
from app.models.user import UserRole
from app.models.work_order import WorkOrder, WorkOrderStatus


def auth(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "ValidPass123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_entry(
    db_session: Session,
    owner_id: int,
    *,
    status: KnowledgeEntryStatus,
    title: str,
    created_at: datetime,
    sync_error: str | None = None,
) -> KnowledgeEntry:
    conversation = Conversation(
        user_id=owner_id,
        dify_conversation_id=f"conversation-{title}",
    )
    db_session.add(conversation)
    db_session.flush()
    record = QARecord(
        conversation_id=conversation.id,
        user_id=owner_id,
        question=title,
        answer="回答",
        retriever_resources=[],
        response_time_ms=10,
    )
    db_session.add(record)
    db_session.flush()
    order = WorkOrder(
        qa_record_id=record.id,
        user_id=owner_id,
        symptom="故障",
        solution="方案",
        status=WorkOrderStatus.CLOSED,
    )
    db_session.add(order)
    db_session.flush()
    entry = KnowledgeEntry(
        work_order_id=order.id,
        title=title,
        content=f"## 故障现象\n{title}\n\n## 解决方案\n方案",
        status=status,
        sync_error=sync_error,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


def test_admin_lists_pending_group_first_and_operator_is_forbidden(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    now = datetime(2026, 8, 7, 10, 0, 0)
    pending = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.PENDING,
        title="pending",
        created_at=now - timedelta(hours=2),
    )
    failed = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.SYNC_FAILED,
        title="failed",
        created_at=now - timedelta(hours=1),
        sync_error="同步失败",
    )
    synced = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.SYNCED,
        title="synced",
        created_at=now,
    )

    assert client.get(
        "/api/v1/knowledge-entries", headers=auth(client, owner.username)
    ).status_code == 403
    response = client.get(
        "/api/v1/knowledge-entries", headers=auth(client, admin.username)
    )

    assert response.status_code == 200
    assert response.json()["page_size"] == 20
    assert response.json()["total"] == 3
    assert [item["id"] for item in response.json()["items"]] == [
        failed.id,
        pending.id,
        synced.id,
    ]
    assert set(response.json()["items"][0]) == {
        "id",
        "work_order_id",
        "title",
        "content",
        "status",
        "dify_document_id",
        "sync_error",
        "synced_at",
        "created_at",
        "updated_at",
    }


def test_admin_edits_failed_entry_back_to_pending_and_synced_is_read_only(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    admin_headers = auth(client, admin.username)
    failed = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.SYNC_FAILED,
        title="旧标题",
        created_at=datetime(2026, 8, 7, 10, 0, 0),
        sync_error="旧错误",
    )
    synced = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.SYNCED,
        title="已同步",
        created_at=datetime(2026, 8, 7, 11, 0, 0),
    )

    response = client.put(
        f"/api/v1/knowledge-entries/{failed.id}",
        headers=admin_headers,
        json={"title": "  新标题  ", "content": "  新正文  "},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "新标题"
    assert response.json()["content"] == "新正文"
    assert response.json()["status"] == "pending"
    assert response.json()["sync_error"] is None
    assert client.put(
        f"/api/v1/knowledge-entries/{synced.id}",
        headers=admin_headers,
        json={"title": "禁止修改", "content": "禁止修改"},
    ).status_code == 409
    assert client.put(
        f"/api/v1/knowledge-entries/{failed.id}",
        headers=admin_headers,
        json={"title": "   ", "content": "正文"},
    ).status_code == 422


def test_knowledge_api_requires_auth_and_reports_missing_entry(
    client: TestClient, add_user
) -> None:
    admin = add_user("Admin01", role=UserRole.ADMIN)
    assert client.get("/api/v1/knowledge-entries").status_code == 401
    assert client.put(
        "/api/v1/knowledge-entries/999999",
        headers=auth(client, admin.username),
        json={"title": "标题", "content": "正文"},
    ).status_code == 404


def test_operator_sync_is_forbidden_before_dataset_configuration_is_checked(
    client: TestClient, add_user, monkeypatch
) -> None:
    operator = add_user("Operator01")
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: Settings(
            _env_file=None,
            app_env="test",
            jwt_secret_key="test-secret-key-long-enough-for-hs256",
            dify_dataset_api_key="",
            dify_dataset_id="",
        ),
    )

    response = client.post(
        "/api/v1/knowledge-entries/999999/sync",
        headers=auth(client, operator.username),
    )

    assert response.status_code == 403


def test_sync_checks_local_entry_before_missing_dataset_configuration(
    client: TestClient, add_user, db_session: Session, monkeypatch
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    synced = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.SYNCED,
        title="已同步",
        created_at=datetime(2026, 8, 7, 12, 0, 0),
    )
    monkeypatch.setattr(
        "app.api.deps.get_settings",
        lambda: Settings(
            _env_file=None,
            app_env="test",
            jwt_secret_key="test-secret-key-long-enough-for-hs256",
            dify_dataset_api_key="",
            dify_dataset_id="",
        ),
    )
    headers = auth(client, admin.username)

    assert client.post(
        "/api/v1/knowledge-entries/999999/sync", headers=headers
    ).status_code == 404
    assert client.post(
        f"/api/v1/knowledge-entries/{synced.id}/sync", headers=headers
    ).status_code == 409


def test_admin_syncs_entry_once_and_synced_becomes_read_only(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    entry = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.PENDING,
        title="连接池超时",
        created_at=datetime(2026, 8, 7, 10, 0, 0),
    )
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path.endswith("/datasets/dataset-1/document/create-by-text")
        assert request.read()
        payload = json.loads(request.content)
        assert payload["name"] == f"连接池超时 [KE-{entry.id}]"
        return httpx.Response(200, json={"document": {"id": "document-1"}})

    dataset_client = DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    )
    app.dependency_overrides[get_dify_dataset_client] = lambda: dataset_client
    try:
        response = client.post(
            f"/api/v1/knowledge-entries/{entry.id}/sync",
            headers=auth(client, admin.username),
        )
        duplicate = client.post(
            f"/api/v1/knowledge-entries/{entry.id}/sync",
            headers=auth(client, admin.username),
        )
    finally:
        dataset_client.close()

    assert response.status_code == 200
    assert response.json()["status"] == "synced"
    assert response.json()["dify_document_id"] == "document-1"
    assert response.json()["synced_at"] is not None
    assert duplicate.status_code == 409
    assert calls == 1


def test_sync_failure_is_persisted_and_timeout_requires_manual_check(
    client: TestClient, add_user, db_session: Session
) -> None:
    owner = add_user("Operator01")
    admin = add_user("Admin01", role=UserRole.ADMIN)
    admin_headers = auth(client, admin.username)
    rejected = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.PENDING,
        title="明确失败",
        created_at=datetime(2026, 8, 7, 10, 0, 0),
    )
    uncertain = add_entry(
        db_session,
        owner.id,
        status=KnowledgeEntryStatus.PENDING,
        title="结果不确定",
        created_at=datetime(2026, 8, 7, 11, 0, 0),
    )

    rejected_client = DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(400, json={"message": "raw secret"})
        ),
    )
    app.dependency_overrides[get_dify_dataset_client] = lambda: rejected_client
    rejected_response = client.post(
        f"/api/v1/knowledge-entries/{rejected.id}/sync",
        headers=admin_headers,
    )
    rejected_client.close()

    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    uncertain_client = DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(timeout_handler),
    )
    app.dependency_overrides[get_dify_dataset_client] = lambda: uncertain_client
    uncertain_response = client.post(
        f"/api/v1/knowledge-entries/{uncertain.id}/sync",
        headers=admin_headers,
    )
    uncertain_client.close()

    db_session.expire_all()
    assert rejected_response.status_code == 502
    assert rejected.status == KnowledgeEntryStatus.SYNC_FAILED
    assert rejected.sync_error == "Dify 未接受知识文档"
    assert "raw secret" not in rejected.sync_error
    assert uncertain_response.status_code == 504
    assert uncertain.status == KnowledgeEntryStatus.SYNC_FAILED
    assert f"[KE-{uncertain.id}]" in (uncertain.sync_error or "")
    assert "Dify 控制台" in (uncertain.sync_error or "")
