from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.bootstrap_service import bootstrap_initial_admin


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return Session(engine)


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        jwt_secret_key="test-secret-key-long-enough-for-hs256",
        initial_admin_enabled=True,
        initial_admin_username="Admin01",
        initial_admin_display_name="系统管理员",
        initial_admin_password="AdminPass123",
    )


def test_bootstrap_creates_initial_admin_once() -> None:
    with make_session() as session:
        settings = make_settings()
        repository = UserRepository(session)

        assert bootstrap_initial_admin(repository, settings) is True
        assert bootstrap_initial_admin(repository, settings) is False

        users, total = repository.list(page=1, page_size=20)
        assert total == 1
        assert len(users) == 1
        assert users[0].username == "admin01"
        assert users[0].role is UserRole.ADMIN
        assert users[0].must_change_password is True
        assert users[0].password_hash != "AdminPass123"


def test_bootstrap_does_nothing_when_disabled() -> None:
    with make_session() as session:
        settings = make_settings().model_copy(update={"initial_admin_enabled": False})
        repository = UserRepository(session)

        assert bootstrap_initial_admin(repository, settings) is False
        assert repository.list(page=1, page_size=20)[1] == 0


def test_bootstrap_rejects_operator_name_conflict() -> None:
    with make_session() as session:
        repository = UserRepository(session)
        repository.add(
            User(
                username="admin01",
                display_name="普通运维人员",
                password_hash=hash_password("Operator123"),
                role=UserRole.OPERATOR,
            )
        )

        try:
            bootstrap_initial_admin(repository, make_settings())
        except RuntimeError as error:
            assert "普通用户" in str(error)
        else:
            raise AssertionError("同名普通用户不应被升级为管理员")
