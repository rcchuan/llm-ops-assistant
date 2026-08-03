import logging

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, validate_password_strength
from app.models.user import User, UserRole
from app.services.user_service import (
    get_user_by_username,
    normalize_display_name,
    normalize_username,
)


logger = logging.getLogger(__name__)


def bootstrap_initial_admin(session: Session, settings: Settings) -> bool:
    if not settings.initial_admin_enabled:
        return False

    password = settings.initial_admin_password.get_secret_value()
    if not all(
        (
            settings.initial_admin_username,
            settings.initial_admin_display_name,
            password,
        )
    ):
        raise RuntimeError("启用初始管理员时必须完整配置用户名、显示姓名和密码")

    username = normalize_username(settings.initial_admin_username)
    display_name = normalize_display_name(settings.initial_admin_display_name)
    validate_password_strength(password)
    existing = get_user_by_username(session, username)
    if existing:
        if existing.role is UserRole.ADMIN:
            return False
        raise RuntimeError("初始管理员用户名已被普通用户占用")

    session.add(
        User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=True,
        )
    )
    session.commit()
    logger.info("初始管理员账号已创建：%s", username)
    return True
