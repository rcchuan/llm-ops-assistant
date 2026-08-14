from datetime import timedelta

import jwt

from app.core.config import Settings
from app.core.exceptions import (
    AdminRequiredError,
    AuthenticationConfigurationError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordChangeRequiredError,
)
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole, utc_now
from app.repositories.user_repository import UserRepository


def login_user(
    repository: UserRepository,
    *,
    username: str,
    password: str,
    settings: Settings,
) -> tuple[User, str, int]:
    user = repository.get_by_username(username)
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    secret_key = _get_secret_key(settings)
    user.last_login_at = utc_now()
    repository.save(user)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        token_version=user.token_version,
        secret_key=secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return user, token, settings.access_token_expire_minutes * 60


def resolve_current_user(
    repository: UserRepository,
    *,
    token: str,
    settings: Settings,
) -> User:
    try:
        claims = decode_access_token(
            token,
            _get_secret_key(settings),
            settings.jwt_algorithm,
        )
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise InvalidCredentialsError from None

    user = repository.get_by_id(user_id)
    if user is None:
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    if (
        claims.get("username") != user.username
        or claims.get("role") != user.role.value
        or claims.get("token_version") != user.token_version
    ):
        raise InvalidCredentialsError
    return user


def change_password(
    repository: UserRepository,
    user: User,
    *,
    current_password: str,
    new_password: str,
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ValueError("当前密码错误")
    if verify_password(new_password, user.password_hash):
        raise ValueError("新密码不能与当前密码相同")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.token_version += 1
    repository.save(user)


def ensure_password_changed(user: User) -> None:
    if user.must_change_password:
        raise PasswordChangeRequiredError


def ensure_admin(user: User) -> None:
    if user.role is not UserRole.ADMIN:
        raise AdminRequiredError


def _get_secret_key(settings: Settings) -> str:
    secret_key = settings.jwt_secret_key.get_secret_value()
    if not secret_key:
        raise AuthenticationConfigurationError
    return secret_key
