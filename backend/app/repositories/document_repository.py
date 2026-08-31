"""Persistence for uploaded documents."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    def get_for_user(self, document_id: uuid.UUID | str, user_id: uuid.UUID) -> Document | None:
        """Scope the lookup by owner so one user can never read another's file."""
        stmt = select(Document).where(Document.id == document_id, Document.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(
        self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[Document], int]:
        count_stmt = select(func.count()).select_from(Document).where(Document.user_id == user_id)
        total = int(self.db.execute(count_stmt).scalar_one())
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).scalars()), total
