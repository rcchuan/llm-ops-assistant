from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.security import hash_password
from app.models.base import Base
from app.models.user import User, UserRole
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

        bootstrap_initial_admin(session, settings)
        bootstrap_initial_admin(session, settings)

        users = session.query(User).all()
        assert len(users) == 1
        assert users[0].username == "admin01"
        assert users[0].role is UserRole.ADMIN
        assert users[0].must_change_password is True


def test_bootstrap_rejects_operator_name_conflict() -> None:
    with make_session() as session:
        session.add(
            User(
                username="admin01",
                display_name="普通运维人员",
                password_hash=hash_password("Operator123"),
                role=UserRole.OPERATOR,
            )
        )
        session.commit()

        try:
            bootstrap_initial_admin(session, make_settings())
        except RuntimeError as error:
            assert "普通用户" in str(error)
        else:
            raise AssertionError("同名普通用户不应被升级为管理员")
