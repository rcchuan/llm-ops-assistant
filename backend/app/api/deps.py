import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole


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

    settings = get_settings()
    secret_key = settings.jwt_secret_key.get_secret_value()
    if not secret_key:
        raise HTTPException(status_code=503, detail="认证服务未配置")
    try:
        claims = decode_access_token(credentials.credentials, secret_key, settings.jwt_algorithm)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    user = session.get(User, user_id)
    if user is None:
        raise unauthorized
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")
    if (
        claims.get("username") != user.username
        or claims.get("role") != user.role.value
        or claims.get("token_version") != user.token_version
    ):
        raise unauthorized
    return user


def require_password_changed(user: User = Depends(get_current_user)) -> User:
    if user.must_change_password:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "PASSWORD_CHANGE_REQUIRED",
                "message": "首次登录必须修改密码",
            },
        )
    return user


def require_admin(user: User = Depends(require_password_changed)) -> User:
    if user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user
