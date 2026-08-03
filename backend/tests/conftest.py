import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-long-enough-for-hs256"
os.environ["INITIAL_ADMIN_ENABLED"] = "false"

from app.core.security import hash_password  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402


@pytest.fixture
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def add_user(db_session: Session):
    def factory(
        username: str,
        *,
        password: str = "ValidPass123",
        role: UserRole = UserRole.OPERATOR,
        is_active: bool = True,
        must_change_password: bool = False,
    ) -> User:
        user = User(
            username=username.lower(),
            display_name=f"{username} 姓名",
            password_hash=hash_password(password),
            role=role,
            is_active=is_active,
            must_change_password=must_change_password,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return factory
