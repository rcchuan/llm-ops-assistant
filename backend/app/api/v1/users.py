from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.security import hash_password, validate_password_strength
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    PasswordReset,
    UserCreate,
    UserList,
    UserRead,
    UserStatusUpdate,
)
from app.services.user_service import (
    create_operator,
    get_user,
    get_user_by_username,
    list_users,
)


router = APIRouter(prefix="/users", tags=["users"])


def operator_or_error(session: Session, user_id: int) -> User:
    user = get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role is not UserRole.OPERATOR:
        raise HTTPException(status_code=403, detail="该操作仅允许用于普通运维人员")
    return user


@router.get("", response_model=UserList)
def read_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=64),
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> UserList:
    users, total = list_users(session, page=page, page_size=page_size, query=q)
    return UserList(items=users, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    user = get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    if get_user_by_username(session, payload.username):
        raise HTTPException(status_code=409, detail="用户名已存在")
    try:
        return create_operator(
            session,
            username=payload.username,
            display_name=payload.display_name,
            initial_password=payload.initial_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="用户名已存在") from None


@router.patch("/{user_id}/status", response_model=UserRead)
def update_status(
    user_id: int,
    payload: UserStatusUpdate,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    user = operator_or_error(session, user_id)
    if user.is_active and not payload.is_active:
        user.token_version += 1
    user.is_active = payload.is_active
    session.commit()
    session.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> MessageResponse:
    user = operator_or_error(session, user_id)
    try:
        validate_password_strength(payload.new_password)
        user.password_hash = hash_password(payload.new_password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    user.must_change_password = True
    user.token_version += 1
    session.commit()
    return MessageResponse(message="密码已重置，用户下次登录必须修改密码")
