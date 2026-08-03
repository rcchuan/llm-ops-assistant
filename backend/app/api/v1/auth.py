from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
)
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user, change_password, record_login


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_db)) -> LoginResponse:
    user = authenticate_user(session, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账号已禁用")

    settings = get_settings()
    secret_key = settings.jwt_secret_key.get_secret_value()
    if not secret_key:
        raise HTTPException(status_code=503, detail="认证服务未配置")
    record_login(session, user)
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role.value,
        token_version=user.token_version,
        secret_key=secret_key,
        algorithm=settings.jwt_algorithm,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    return LoginResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
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
            session,
            user,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    return MessageResponse(message="密码修改成功，请重新登录")
