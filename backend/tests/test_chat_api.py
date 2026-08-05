from collections import deque

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_dify_client
from app.integrations.dify.exceptions import (
    DifyConfigurationError,
    DifyInvalidResponseError,
    DifyTimeoutError,
    DifyUnavailableError,
)
from app.integrations.dify.schemas import DifyChatResult
from app.main import app
from app.models.user import UserRole


class FakeDifyClient:
    def __init__(self, *results: DifyChatResult | Exception):
        self.results = deque(results)

    def chat(self, **_kwargs) -> DifyChatResult:
        result = self.results.popleft()
        if isinstance(result, Exception):
            raise result
        return result


def result(conversation_id: str, answer: str) -> DifyChatResult:
    return DifyChatResult(
        answer=answer,
        conversation_id=conversation_id,
        message_id="message-1",
        resources=[],
    )


def use_dify(fake: FakeDifyClient) -> None:
    def override():
        yield fake

    app.dependency_overrides[get_dify_client] = override


def login(client: TestClient, username: str, password: str = "ValidPass123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_feedback_cors_preflight_allows_put(client) -> None:
    response = client.options(
        "/api/v1/chat/messages/1/feedback",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "PUT",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_chat_requires_login_and_completed_password_change(client, add_user) -> None:
    assert client.get("/api/v1/chat/current").status_code == 401

    add_user("Operator01", must_change_password=True)
    token = login(client, "operator01")
    response = client.get("/api/v1/chat/current", headers=headers(token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"


@pytest.mark.parametrize("role", [UserRole.OPERATOR, UserRole.ADMIN])
def test_user_can_chat_restore_start_new_view_history_and_update_feedback(
    client,
    add_user,
    role: UserRole,
) -> None:
    user = add_user("Operator01" if role is UserRole.OPERATOR else "Admin01", role=role)
    token = login(client, user.username)
    auth = headers(token)
    use_dify(FakeDifyClient(result("dify-1", "第一轮回答"), result("dify-2", "新对话回答")))

    first = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": " 第一轮问题 ", "start_new": False},
    )
    assert first.status_code == 200
    assert first.json()["question"] == "第一轮问题"
    assert first.json()["persisted"] is True
    assert first.json()["conversation_locked"] is False
    assert "dify_message_id" not in first.text
    assert "dify_conversation_id" not in first.text

    current = client.get("/api/v1/chat/current", headers=auth)
    assert current.status_code == 200
    assert [item["answer"] for item in current.json()["messages"]] == ["第一轮回答"]

    new_state = client.post("/api/v1/chat/new", headers=auth)
    assert new_state.status_code == 200
    assert new_state.json() == {"message": "已开始新对话"}

    second = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "新问题", "start_new": True},
    )
    assert second.status_code == 200

    history = client.get("/api/v1/chat/history?limit=50", headers=auth)
    assert history.status_code == 200
    assert [item["question"] for item in history.json()["items"]] == [
        "新问题",
        "第一轮问题",
    ]

    feedback = client.put(
        f"/api/v1/chat/messages/{second.json()['id']}/feedback",
        headers=auth,
        json={"feedback": "helpful"},
    )
    assert feedback.status_code == 200
    assert feedback.json()["feedback"] == "helpful"


def test_chat_validates_question(client, add_user) -> None:
    user = add_user("Operator01")
    auth = headers(login(client, user.username))
    use_dify(FakeDifyClient())

    assert client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "   "},
    ).status_code == 422
    assert client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "x" * 1001},
    ).status_code == 422


def test_chat_data_and_feedback_are_isolated_by_user(client, add_user) -> None:
    first_user = add_user("Operator01")
    second_user = add_user("Operator02")
    first_auth = headers(login(client, first_user.username))
    second_auth = headers(login(client, second_user.username))
    use_dify(FakeDifyClient(result("dify-1", "用户一回答"), result("dify-2", "用户二回答")))

    first = client.post(
        "/api/v1/chat/messages",
        headers=first_auth,
        json={"question": "用户一问题"},
    ).json()
    client.post(
        "/api/v1/chat/messages",
        headers=second_auth,
        json={"question": "用户二问题"},
    )

    second_history = client.get("/api/v1/chat/history", headers=second_auth).json()
    assert [item["question"] for item in second_history["items"]] == ["用户二问题"]
    assert client.put(
        f"/api/v1/chat/messages/{first['id']}/feedback",
        headers=second_auth,
        json={"feedback": "helpful"},
    ).status_code == 404


@pytest.mark.parametrize(
    ("error", "status_code", "detail"),
    [
        (DifyTimeoutError("secret"), 504, "回答生成超时，请稍后重试"),
        (DifyConfigurationError("secret"), 503, "问答服务未配置或认证失败"),
        (DifyUnavailableError("secret"), 503, "问答服务暂时不可用，请稍后重试"),
        (DifyInvalidResponseError("secret"), 502, "问答服务返回数据不完整，请稍后重试"),
    ],
)
def test_chat_maps_dify_errors_without_saving_or_leaking(
    client,
    add_user,
    error: Exception,
    status_code: int,
    detail: str,
) -> None:
    user = add_user("Operator01")
    auth = headers(login(client, user.username))
    use_dify(FakeDifyClient(error))

    response = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "问题"},
    )

    assert response.status_code == status_code
    assert response.json()["detail"] == detail
    assert "secret" not in response.text
    assert client.get("/api/v1/chat/current", headers=auth).json()["messages"] == []


def test_chat_returns_generated_answer_without_feedback_id_when_save_fails(
    client,
    add_user,
    db_session: Session,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    auth = headers(login(client, user.username))
    use_dify(FakeDifyClient(result("dify-1", "已生成回答")))

    def fail_commit() -> None:
        raise SQLAlchemyError("secret database detail")

    monkeypatch.setattr(db_session, "commit", fail_commit)
    response = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "问题"},
    )

    assert response.status_code == 200
    assert response.json()["id"] is None
    assert response.json()["persisted"] is False
    assert response.json()["conversation_locked"] is True
    assert response.json()["answer"] == "已生成回答"
    assert "secret" not in response.text


def test_chat_returns_uncertain_generated_answer_when_refresh_fails(
    client,
    add_user,
    db_session: Session,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    auth = headers(login(client, user.username))
    fake = FakeDifyClient(result("dify-1", "已生成但保存状态未知"))
    use_dify(fake)

    def fail_refresh(_instance) -> None:
        raise SQLAlchemyError("secret database detail")

    monkeypatch.setattr(db_session, "refresh", fail_refresh)
    response = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "问题"},
    )

    assert response.status_code == 200
    assert response.json()["id"] is None
    assert response.json()["persisted"] is None
    assert response.json()["conversation_locked"] is True
    assert response.json()["answer"] == "已生成但保存状态未知"
    assert len(fake.results) == 0
    assert "secret" not in response.text


def test_feedback_returns_stable_uncertain_error_when_refresh_fails(
    client,
    add_user,
    db_session: Session,
    monkeypatch,
) -> None:
    user = add_user("Operator01")
    auth = headers(login(client, user.username))
    use_dify(FakeDifyClient(result("dify-1", "回答")))
    record_id = client.post(
        "/api/v1/chat/messages",
        headers=auth,
        json={"question": "问题"},
    ).json()["id"]

    def fail_refresh(_instance) -> None:
        raise SQLAlchemyError("secret database detail")

    monkeypatch.setattr(db_session, "refresh", fail_refresh)
    response = client.put(
        f"/api/v1/chat/messages/{record_id}/feedback",
        headers=auth,
        json={"feedback": "helpful"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "反馈保存状态无法确认，请刷新页面确认"
    assert "secret" not in response.text
    history = client.get("/api/v1/chat/history", headers=auth)
    assert history.json()["items"][0]["feedback"] == "helpful"
