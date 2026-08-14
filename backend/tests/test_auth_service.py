import pytest
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import (
    AdminRequiredError,
    AuthenticationConfigurationError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordChangeRequiredError,
)
from app.core.security import decode_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import (
    change_password,
    ensure_admin,
    ensure_password_changed,
    login_user,
    resolve_current_user,
)


def make_settings(secret_key: str = "test-secret-key-long-enough-for-hs256") -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        jwt_secret_key=secret_key,
        initial_admin_enabled=False,
    )


def add_user(
    repository: UserRepository,
    *,
    is_active: bool = True,
    must_change_password: bool = False,
) -> User:
    return repository.add(
        User(
            username="operator01",
            display_name="一号运维",
            password_hash=hash_password("ValidPass123"),
            role=UserRole.OPERATOR,
            is_active=is_active,
            must_change_password=must_change_password,
        )
    )


def test_login_authenticates_records_time_and_issues_token(db_session: Session) -> None:
    repository = UserRepository(db_session)
    user = add_user(repository)
    settings = make_settings()

    logged_in, token, expires_in = login_user(
        repository,
        username="OPERATOR01",
        password="ValidPass123",
        settings=settings,
    )

    claims = decode_access_token(
        token,
        settings.jwt_secret_key.get_secret_value(),
        settings.jwt_algorithm,
    )
    assert logged_in is user
    assert user.last_login_at is not None
    assert claims["sub"] == str(user.id)
    assert claims["token_version"] == 0
    assert expires_in == 7200


def test_login_rejects_wrong_password_disabled_user_and_missing_config(
    db_session: Session,
) -> None:
    repository = UserRepository(db_session)
    user = add_user(repository)

    with pytest.raises(InvalidCredentialsError):
        login_user(
            repository,
            username=user.username,
            password="WrongPass123",
            settings=make_settings(),
        )

    user.is_active = False
    repository.save(user)
    with pytest.raises(InactiveUserError):
        login_user(
            repository,
            username=user.username,
            password="ValidPass123",
            settings=make_settings(),
        )

    user.is_active = True
    repository.save(user)
    with pytest.raises(AuthenticationConfigurationError):
        login_user(
            repository,
            username=user.username,
            password="ValidPass123",
            settings=make_settings(""),
        )


def test_current_user_rechecks_claims_and_database_state(db_session: Session) -> None:
    repository = UserRepository(db_session)
    user = add_user(repository)
    settings = make_settings()
    _, token, _ = login_user(
        repository,
        username=user.username,
        password="ValidPass123",
        settings=settings,
    )

    assert resolve_current_user(repository, token=token, settings=settings) is user

    user.token_version += 1
    repository.save(user)
    with pytest.raises(InvalidCredentialsError):
        resolve_current_user(repository, token=token, settings=settings)

    with pytest.raises(InvalidCredentialsError):
        resolve_current_user(repository, token="invalid-token", settings=settings)

    user.is_active = False
    repository.save(user)
    _, fresh_token, _ = login_user_for_inactive_check(repository, user, settings)
    with pytest.raises(InactiveUserError):
        resolve_current_user(repository, token=fresh_token, settings=settings)


def login_user_for_inactive_check(
    repository: UserRepository,
    user: User,
    settings: Settings,
) -> tuple[User, str, int]:
    user.is_active = True
    repository.save(user)
    result = login_user(
        repository,
        username=user.username,
        password="ValidPass123",
        settings=settings,
    )
    user.is_active = False
    repository.save(user)
    return result


def test_change_password_clears_forced_state_and_revokes_tokens(
    db_session: Session,
) -> None:
    repository = UserRepository(db_session)
    user = add_user(repository, must_change_password=True)

    with pytest.raises(ValueError, match="当前密码错误"):
        change_password(
            repository,
            user,
            current_password="WrongPass123",
            new_password="NewPass123",
        )
    with pytest.raises(ValueError, match="新密码不能与当前密码相同"):
        change_password(
            repository,
            user,
            current_password="ValidPass123",
            new_password="ValidPass123",
        )

    change_password(
        repository,
        user,
        current_password="ValidPass123",
        new_password="NewPass123",
    )

    assert verify_password("NewPass123", user.password_hash)
    assert user.must_change_password is False
    assert user.token_version == 1


def test_authorization_rules_do_not_require_fastapi(db_session: Session) -> None:
    repository = UserRepository(db_session)
    operator = add_user(repository, must_change_password=True)

    with pytest.raises(PasswordChangeRequiredError):
        ensure_password_changed(operator)

    operator.must_change_password = False
    with pytest.raises(AdminRequiredError):
        ensure_admin(operator)

    operator.role = UserRole.ADMIN
    ensure_password_changed(operator)
    ensure_admin(operator)
