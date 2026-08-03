import jwt
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import UserRole


def login(client: TestClient, username: str, password: str = "ValidPass123") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_login_success_failure_and_disabled_user(client, add_user, db_session: Session) -> None:
    user = add_user("Operator01")

    payload = login(client, "OPERATOR01")

    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 7200
    assert payload["user"]["username"] == "operator01"
    assert "password_hash" not in payload["user"]
    db_session.refresh(user)
    assert user.last_login_at is not None

    for body in (
        {"username": "missing01", "password": "ValidPass123"},
        {"username": "operator01", "password": "WrongPass123"},
    ):
        response = client.post("/api/v1/auth/login", json=body)
        assert response.status_code == 401
        assert response.json()["detail"] == "用户名或密码错误"

    add_user("Disabled01", is_active=False)
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "disabled01", "password": "ValidPass123"},
    )
    assert response.status_code == 403


def test_me_requires_valid_token_and_rechecks_active_state(client, add_user, db_session) -> None:
    user = add_user("Operator01")
    token = login(client, user.username)["access_token"]

    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get(
        "/api/v1/auth/me", headers=auth_header("invalid-token")
    ).status_code == 401

    user.is_active = False
    db_session.commit()
    assert client.get("/api/v1/auth/me", headers=auth_header(token)).status_code == 403


def test_admin_creates_and_reads_operator_without_exposing_hash(client, add_user) -> None:
    add_user("Admin01", role=UserRole.ADMIN)
    token = login(client, "admin01")["access_token"]
    headers = auth_header(token)

    created = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "NewOperator01",
            "display_name": " 新运维人员 ",
            "initial_password": "Initial123",
        },
    )

    assert created.status_code == 201
    assert created.json()["role"] == "operator"
    assert created.json()["username"] == "newoperator01"
    assert created.json()["display_name"] == "新运维人员"
    assert created.json()["must_change_password"] is True
    assert created.json()["created_at"].endswith(("Z", "+00:00"))
    assert "password_hash" not in created.text

    detail = client.get(f"/api/v1/users/{created.json()['id']}", headers=headers)
    listing = client.get("/api/v1/users?page=1&page_size=20", headers=headers)
    assert detail.status_code == 200
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert "password_hash" not in listing.text

    duplicate = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "NEWOPERATOR01",
            "display_name": "重复用户",
            "initial_password": "Initial123",
        },
    )
    assert duplicate.status_code == 409

    create_admin = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "username": "OtherAdmin",
            "display_name": "其他管理员",
            "initial_password": "Initial123",
            "role": "admin",
        },
    )
    assert create_admin.status_code == 422


def test_operator_and_forced_password_user_cannot_manage_users(client, add_user) -> None:
    add_user("Operator01")
    operator_token = login(client, "operator01")["access_token"]
    assert client.get(
        "/api/v1/users", headers=auth_header(operator_token)
    ).status_code == 403

    add_user("Admin01", role=UserRole.ADMIN, must_change_password=True)
    forced_token = login(client, "admin01")["access_token"]
    response = client.get("/api/v1/users", headers=auth_header(forced_token))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_admin_can_disable_enable_and_reset_operator(client, add_user, db_session) -> None:
    add_user("Admin01", role=UserRole.ADMIN)
    operator = add_user("Operator01")
    operator_token = login(client, "operator01")["access_token"]
    admin_token = login(client, "admin01")["access_token"]
    headers = auth_header(admin_token)

    disabled = client.patch(
        f"/api/v1/users/{operator.id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert client.get(
        "/api/v1/auth/me", headers=auth_header(operator_token)
    ).status_code == 403

    assert client.patch(
        f"/api/v1/users/{operator.id}/status",
        headers=headers,
        json={"is_active": True},
    ).status_code == 200
    assert client.get(
        "/api/v1/auth/me", headers=auth_header(operator_token)
    ).status_code == 401

    new_token = login(client, "operator01")["access_token"]
    assert client.get(
        "/api/v1/auth/me", headers=auth_header(new_token)
    ).status_code == 200

    reset = client.post(
        f"/api/v1/users/{operator.id}/reset-password",
        headers=headers,
        json={"new_password": "ResetPass123"},
    )
    assert reset.status_code == 200
    db_session.refresh(operator)
    assert operator.must_change_password is True
    assert "ResetPass123" not in reset.text
    for path, method, body in (
        ("/api/v1/auth/me", client.get, None),
        (
            "/api/v1/auth/change-password",
            client.post,
            {"current_password": "ValidPass123", "new_password": "OtherPass123"},
        ),
    ):
        response = method(path, headers=auth_header(new_token), json=body) if body else method(
            path, headers=auth_header(new_token)
        )
        assert response.status_code == 401


def test_admin_cannot_manage_another_admin(client, add_user) -> None:
    first = add_user("Admin01", role=UserRole.ADMIN)
    second = add_user("Admin02", role=UserRole.ADMIN)
    headers = auth_header(login(client, first.username)["access_token"])

    assert client.patch(
        f"/api/v1/users/{second.id}/status",
        headers=headers,
        json={"is_active": False},
    ).status_code == 403
    assert client.post(
        f"/api/v1/users/{second.id}/reset-password",
        headers=headers,
        json={"new_password": "ResetPass123"},
    ).status_code == 403


def test_change_password_validates_current_and_clears_forced_state(
    client, add_user, db_session
) -> None:
    user = add_user("Operator01", must_change_password=True)
    token = login(client, user.username)["access_token"]
    headers = auth_header(token)

    assert client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongPass123", "new_password": "NewPass123"},
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "ValidPass123", "new_password": "ValidPass123"},
    ).status_code == 400

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "ValidPass123", "new_password": "NewPass123"},
    )
    assert changed.status_code == 200
    assert "NewPass123" not in changed.text
    db_session.refresh(user)
    assert user.must_change_password is False
    assert client.get(
        "/api/v1/auth/me", headers=auth_header(token)
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/change-password",
        headers=auth_header(token),
        json={"current_password": "NewPass123", "new_password": "OtherPass123"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "ValidPass123"},
    ).status_code == 401
    new_login = client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "NewPass123"},
    )
    assert new_login.status_code == 200
    assert client.get(
        "/api/v1/auth/me",
        headers=auth_header(new_login.json()["access_token"]),
    ).status_code == 200


def test_token_version_mismatch_returns_401(client, add_user, db_session) -> None:
    user = add_user("Operator01")
    token = login(client, user.username)["access_token"]
    user.token_version += 1
    db_session.commit()

    response = client.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert "token_version" not in response.text


def test_token_without_version_returns_401(client, add_user) -> None:
    user = add_user("Operator01")
    token = jwt.encode(
        {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value,
            "exp": 4102444800,
        },
        "test-secret-key-long-enough-for-hs256",
        algorithm="HS256",
    )

    response = client.get("/api/v1/auth/me", headers=auth_header(token))

    assert response.status_code == 401
    assert "token_version" not in response.text


def test_errors_do_not_leak_secrets(client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "missing01", "password": "SecretPass123"},
    )
    text = response.text.lower()
    assert "secretpass123" not in text
    assert "mysql+pymysql" not in text
    assert "test-secret-key" not in text
