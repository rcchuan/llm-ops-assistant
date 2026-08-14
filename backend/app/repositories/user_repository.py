from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        normalized = username.strip().lower()
        return self.session.scalar(select(User).where(User.username == normalized))

    def list(
        self,
        *,
        page: int,
        page_size: int,
        query: str | None = None,
    ) -> tuple[list[User], int]:
        statement = select(User)
        count_statement = select(func.count()).select_from(User)
        if query and (normalized_query := query.strip()):
            pattern = f"%{normalized_query}%"
            condition = or_(
                User.username.ilike(pattern),
                User.display_name.ilike(pattern),
            )
            statement = statement.where(condition)
            count_statement = count_statement.where(condition)
        users = self.session.scalars(
            statement.order_by(User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(users), self.session.scalar(count_statement) or 0

    def add(self, user: User) -> User:
        self.session.add(user)
        return self._commit_and_refresh(user)

    def save(self, user: User) -> User:
        return self._commit_and_refresh(user)

    def _commit_and_refresh(self, user: User) -> User:
        try:
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
            raise
        self.session.refresh(user)
        return user
