from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.exceptions import (
    OperatorOnlyOperationError,
    UsernameAlreadyExistsError,
    UserNotFoundError,
)
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
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
    list_users,
    reset_operator_password,
    update_operator_status,
)


router = APIRouter(prefix="/users", tags=["users"])


def map_user_operation_error(error: Exception) -> NoReturn:
    if isinstance(error, UserNotFoundError):
        raise HTTPException(status_code=404, detail="用户不存在") from None
    if isinstance(error, OperatorOnlyOperationError):
        raise HTTPException(
            status_code=403,
            detail="该操作仅允许用于普通运维人员",
        ) from None
    raise error


@router.get("", response_model=UserList)
def read_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=64),
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> UserList:
    users, total = list_users(
        UserRepository(session),
        page=page,
        page_size=page_size,
        query=q,
    )
    return UserList(items=users, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    try:
        return get_user(UserRepository(session), user_id)
    except UserNotFoundError as error:
        map_user_operation_error(error)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    payload: UserCreate,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    try:
        return create_operator(
            UserRepository(session),
            username=payload.username,
            display_name=payload.display_name,
            initial_password=payload.initial_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except UsernameAlreadyExistsError:
        raise HTTPException(status_code=409, detail="用户名已存在") from None


@router.patch("/{user_id}/status", response_model=UserRead)
def update_status(
    user_id: int,
    payload: UserStatusUpdate,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> User:
    try:
        return update_operator_status(
            UserRepository(session),
            user_id,
            is_active=payload.is_active,
        )
    except (UserNotFoundError, OperatorOnlyOperationError) as error:
        map_user_operation_error(error)


@router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    _admin: User = Depends(require_admin),
    session: Session = Depends(get_db),
) -> MessageResponse:
    try:
        reset_operator_password(
            UserRepository(session),
            user_id,
            new_password=payload.new_password,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except (UserNotFoundError, OperatorOnlyOperationError) as error:
        map_user_operation_error(error)
    return MessageResponse(message="密码已重置，用户下次登录必须修改密码")
