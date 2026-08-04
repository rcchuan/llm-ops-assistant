from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


def make_user(username: str, display_name: str) -> User:
    return User(
        username=username,
        display_name=display_name,
        password_hash="not-a-real-hash",
        role=UserRole.OPERATOR,
    )


def test_repository_gets_users_by_id_and_normalized_username(
    db_session: Session,
) -> None:
    repository = UserRepository(db_session)
    user = repository.add(make_user("operator01", "一号运维"))

    assert repository.get_by_id(user.id) is user
    assert repository.get_by_username("  OPERATOR01  ") is user


def test_repository_lists_and_filters_users(db_session: Session) -> None:
    repository = UserRepository(db_session)
    repository.add(make_user("operator01", "网络运维"))
    repository.add(make_user("operator02", "数据库运维"))
    repository.add(make_user("observer01", "只读人员"))

    users, total = repository.list(page=2, page_size=2)
    assert [user.username for user in users] == ["observer01"]
    assert total == 3

    users, total = repository.list(page=1, page_size=20, query="数据库")
    assert [user.username for user in users] == ["operator02"]
    assert total == 1

    users, total = repository.list(page=1, page_size=20, query="OPERATOR")
    assert [user.username for user in users] == ["operator01", "operator02"]
    assert total == 2


def test_repository_adds_and_saves_user(db_session: Session) -> None:
    repository = UserRepository(db_session)
    user = repository.add(make_user("operator01", "原姓名"))
    assert user.id is not None

    user.display_name = "新姓名"
    saved = repository.save(user)
    db_session.expire_all()

    assert saved.id == user.id
    assert repository.get_by_id(user.id).display_name == "新姓名"
