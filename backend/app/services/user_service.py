from sqlalchemy.exc import IntegrityError

from app.core.exceptions import (
    OperatorOnlyOperationError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import hash_password, validate_password_strength
from app.core.user_validation import normalize_display_name, normalize_username
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


def get_user(repository: UserRepository, user_id: int) -> User:
    user = repository.get_by_id(user_id)
    if user is None:
        raise UserNotFoundError
    return user


def list_users(
    repository: UserRepository,
    *,
    page: int,
    page_size: int,
    query: str | None = None,
) -> tuple[list[User], int]:
    return repository.list(page=page, page_size=page_size, query=query)


def create_operator(
    repository: UserRepository,
    *,
    username: str,
    display_name: str,
    initial_password: str,
) -> User:
    username = normalize_username(username)
    if repository.get_by_username(username):
        raise UsernameAlreadyExistsError
    validate_password_strength(initial_password)
    user = User(
        username=username,
        display_name=normalize_display_name(display_name),
        password_hash=hash_password(initial_password),
        role=UserRole.OPERATOR,
        is_active=True,
        must_change_password=True,
    )
    try:
        return repository.add(user)
    except IntegrityError:
        raise UsernameAlreadyExistsError from None


def _get_operator(repository: UserRepository, user_id: int) -> User:
    user = get_user(repository, user_id)
    if user.role is not UserRole.OPERATOR:
        raise OperatorOnlyOperationError
    return user


def update_operator_status(
    repository: UserRepository,
    user_id: int,
    *,
    is_active: bool,
) -> User:
    user = _get_operator(repository, user_id)
    if user.is_active and not is_active:
        user.token_version += 1
    user.is_active = is_active
    return repository.save(user)


def reset_operator_password(
    repository: UserRepository,
    user_id: int,
    *,
    new_password: str,
) -> User:
    user = _get_operator(repository, user_id)
    validate_password_strength(new_password)
    user.password_hash = hash_password(new_password)
    user.must_change_password = True
    user.token_version += 1
    return repository.save(user)
