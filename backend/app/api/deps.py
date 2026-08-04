from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import (
    AdminRequiredError,
    AuthenticationConfigurationError,
    InactiveUserError,
    InvalidCredentialsError,
    PasswordChangeRequiredError,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import (
    ensure_admin,
    ensure_password_changed,
    resolve_current_user,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证凭证无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized

    try:
        return resolve_current_user(
            UserRepository(session),
            token=credentials.credentials,
            settings=get_settings(),
        )
    except InvalidCredentialsError:
        raise unauthorized from None
    except InactiveUserError:
        raise HTTPException(status_code=403, detail="账号已禁用")
    except AuthenticationConfigurationError:
        raise HTTPException(status_code=503, detail="认证服务未配置") from None


def require_password_changed(user: User = Depends(get_current_user)) -> User:
    try:
        ensure_password_changed(user)
    except PasswordChangeRequiredError:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PASSWORD_CHANGE_REQUIRED",
                "message": "首次登录必须修改密码",
            },
        ) from None
    return user


def require_admin(user: User = Depends(require_password_changed)) -> User:
    try:
        ensure_admin(user)
    except AdminRequiredError:
        raise HTTPException(status_code=403, detail="需要管理员权限") from None
    return user
