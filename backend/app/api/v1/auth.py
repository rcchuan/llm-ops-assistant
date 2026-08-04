from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationConfigurationError,
    InactiveUserError,
    InvalidCredentialsError,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
)
from app.schemas.user import UserRead
from app.repositories.user_repository import UserRepository
from app.services.auth_service import change_password, login_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> LoginResponse:
    try:
        user, token, expires_in = login_user(
            UserRepository(session),
            username=payload.username,
            password=payload.password,
            settings=get_settings(),
        )
    except InvalidCredentialsError:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    except InactiveUserError:
        raise HTTPException(status_code=403, detail="账号已禁用")
    except AuthenticationConfigurationError:
        raise HTTPException(status_code=503, detail="认证服务未配置") from None
    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", response_model=MessageResponse)
def update_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> MessageResponse:
    try:
        change_password(
            UserRepository(session),
            user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return MessageResponse(message="密码修改成功，请重新登录")
