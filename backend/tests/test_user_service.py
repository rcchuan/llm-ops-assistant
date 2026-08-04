import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import (
    OperatorOnlyOperationError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.user_service import (
    create_operator,
    get_user,
    list_users,
    reset_operator_password,
    update_operator_status,
)


def add_user(
    repository: UserRepository,
    username: str,
    *,
    role: UserRole = UserRole.OPERATOR,
    is_active: bool = True,
) -> User:
    return repository.add(
        User(
            username=username,
            display_name=f"{username} 姓名",
            password_hash=hash_password("ValidPass123"),
            role=role,
            is_active=is_active,
        )
    )


def test_service_creates_only_normalized_operator(db_session: Session) -> None:
    repository = UserRepository(db_session)

    user = create_operator(
        repository,
        username="  NewOperator01  ",
        display_name=" 新运维人员 ",
        initial_password="Initial123",
    )

    assert user.username == "newoperator01"
    assert user.display_name == "新运维人员"
    assert user.role is UserRole.OPERATOR
    assert user.is_active is True
    assert user.must_change_password is True
    assert verify_password("Initial123", user.password_hash)

    with pytest.raises(UsernameAlreadyExistsError):
        create_operator(
            repository,
            username="NEWOPERATOR01",
            display_name="重复用户",
            initial_password="Initial123",
        )


def test_service_gets_and_lists_users(db_session: Session) -> None:
    repository = UserRepository(db_session)
    operator = add_user(repository, "operator01")

    assert get_user(repository, operator.id) is operator
    users, total = list_users(repository, page=1, page_size=20, query="operator")
    assert users == [operator]
    assert total == 1

    with pytest.raises(UserNotFoundError):
        get_user(repository, 999)


def test_service_only_changes_operator_status_and_revokes_on_disable(
    db_session: Session,
) -> None:
    repository = UserRepository(db_session)
    operator = add_user(repository, "operator01")
    admin = add_user(repository, "admin01", role=UserRole.ADMIN)

    disabled = update_operator_status(repository, operator.id, is_active=False)
    assert disabled.is_active is False
    assert disabled.token_version == 1

    disabled_again = update_operator_status(repository, operator.id, is_active=False)
    assert disabled_again.token_version == 1

    enabled = update_operator_status(repository, operator.id, is_active=True)
    assert enabled.is_active is True
    assert enabled.token_version == 1

    with pytest.raises(OperatorOnlyOperationError):
        update_operator_status(repository, admin.id, is_active=False)
    with pytest.raises(UserNotFoundError):
        update_operator_status(repository, 999, is_active=False)


def test_service_resets_operator_password_and_revokes_tokens(
    db_session: Session,
) -> None:
    repository = UserRepository(db_session)
    operator = add_user(repository, "operator01")
    admin = add_user(repository, "admin01", role=UserRole.ADMIN)

    reset_operator_password(repository, operator.id, new_password="ResetPass123")

    assert verify_password("ResetPass123", operator.password_hash)
    assert operator.must_change_password is True
    assert operator.token_version == 1
    with pytest.raises(OperatorOnlyOperationError):
        reset_operator_password(repository, admin.id, new_password="ResetPass123")
