import logging

from app.core.config import Settings
from app.core.security import hash_password, validate_password_strength
from app.core.user_validation import normalize_display_name, normalize_username
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


def bootstrap_initial_admin(repository: UserRepository, settings: Settings) -> bool:
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
    existing = repository.get_by_username(username)
    if existing:
        if existing.role is UserRole.ADMIN:
            return False
        raise RuntimeError("初始管理员用户名已被普通用户占用")

    repository.add(
        User(
            username=username,
            display_name=display_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
            must_change_password=True,
        )
    )
    logger.info("初始管理员账号已创建：%s", username)
    return True
