import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_strength
from app.models.user import User, UserRole


USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def normalize_username(username: str) -> str:
    normalized = username.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError("用户名须以字母开头，仅含字母、数字、下划线，长度 4～32 位")
    return normalized


def normalize_display_name(display_name: str) -> str:
    normalized = display_name.strip()
    if not normalized:
        raise ValueError("显示姓名不能为空")
    if len(normalized) > 64:
        raise ValueError("显示姓名不能超过 64 位")
    return normalized


def get_user_by_username(session: Session, username: str) -> User | None:
    normalized = username.strip().lower()
    return session.scalar(select(User).where(User.username == normalized))


def get_user(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def list_users(
    session: Session,
    *,
    page: int,
    page_size: int,
    query: str | None = None,
) -> tuple[list[User], int]:
    statement = select(User)
    count_statement = select(func.count()).select_from(User)
    if query and (normalized_query := query.strip()):
        pattern = f"%{normalized_query}%"
        condition = or_(
            User.username.ilike(pattern),
            User.display_name.ilike(pattern),
        )
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    users = session.scalars(
        statement.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(users), session.scalar(count_statement) or 0


def create_operator(
    session: Session,
    *,
    username: str,
    display_name: str,
    initial_password: str,
) -> User:
    validate_password_strength(initial_password)
    user = User(
        username=normalize_username(username),
        display_name=normalize_display_name(display_name),
        password_hash=hash_password(initial_password),
        role=UserRole.OPERATOR,
        is_active=True,
        must_change_password=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
