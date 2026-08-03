from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, utc_now
from app.services.user_service import get_user_by_username


def authenticate_user(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def record_login(session: Session, user: User) -> None:
    user.last_login_at = utc_now()
    session.commit()
    session.refresh(user)


def change_password(
    session: Session,
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
    session.commit()
