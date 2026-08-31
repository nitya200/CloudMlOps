"""Persistence for users and their sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models import Session as SessionModel
from app.models import User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        return self.db.execute(stmt).scalar_one_or_none()

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def list_users(
        self,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)

        if search:
            pattern = f"%{search.strip().lower()}%"
            condition = func.lower(User.name).like(pattern) | func.lower(User.email).like(pattern)
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if role:
            stmt = stmt.where(User.role == role)
            count_stmt = count_stmt.where(User.role == role)

        total = int(self.db.execute(count_stmt).scalar_one())
        stmt = stmt.order_by(User.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(stmt).scalars()), total

    def count_active(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))
        return int(self.db.execute(stmt).scalar_one())


class SessionRepository(BaseRepository[SessionModel]):
    model = SessionModel

    def get_by_token_id(self, token_id: str) -> SessionModel | None:
        stmt = select(SessionModel).where(SessionModel.token_id == token_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, token_id: str) -> bool:
        session = self.get_by_token_id(token_id)
        if session is None:
            return False
        session.revoked = True
        self.db.flush()
        return True

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(SessionModel).where(
            SessionModel.user_id == user_id, SessionModel.revoked.is_(False)
        )
        sessions = list(self.db.execute(stmt).scalars())
        for session in sessions:
            session.revoked = True
        self.db.flush()
        return len(sessions)
