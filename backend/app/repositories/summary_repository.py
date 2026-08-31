"""Persistence for summary requests, summaries and the history view."""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.models import RequestStatus, Summary, SummaryRequest
from app.repositories.base import BaseRepository


class SummaryRequestRepository(BaseRepository[SummaryRequest]):
    model = SummaryRequest

    def get_for_user(self, request_id: uuid.UUID, user_id: uuid.UUID) -> SummaryRequest | None:
        stmt = select(SummaryRequest).where(
            SummaryRequest.id == request_id, SummaryRequest.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def count_by_status(self, status: RequestStatus) -> int:
        stmt = (
            select(func.count()).select_from(SummaryRequest).where(SummaryRequest.status == status)
        )
        return int(self.db.execute(stmt).scalar_one())


class SummaryRepository(BaseRepository[Summary]):
    model = Summary

    def _with_request(self):
        return select(Summary).options(
            joinedload(Summary.request).joinedload(SummaryRequest.document)
        )

    def get_for_user(self, summary_id: uuid.UUID | str, user_id: uuid.UUID) -> Summary | None:
        """Ownership is enforced in SQL, not after the fact in Python."""
        stmt = (
            self._with_request()
            .join(SummaryRequest, Summary.request_id == SummaryRequest.id)
            .where(Summary.id == summary_id, SummaryRequest.user_id == user_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_by_request(self, request_id: uuid.UUID) -> Summary | None:
        stmt = select(Summary).where(Summary.request_id == request_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def search_history(
        self,
        user_id: uuid.UUID,
        *,
        search: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[Summary], int]:
        """Newest-first, optionally full-text-ish filtered, page of history."""
        base = select(Summary).join(SummaryRequest, Summary.request_id == SummaryRequest.id)
        count_stmt = (
            select(func.count())
            .select_from(Summary)
            .join(SummaryRequest, Summary.request_id == SummaryRequest.id)
            .where(SummaryRequest.user_id == user_id)
        )
        base = base.where(SummaryRequest.user_id == user_id)

        if search and search.strip():
            pattern = f"%{search.strip().lower()}%"
            condition = or_(
                func.lower(SummaryRequest.title).like(pattern),
                func.lower(Summary.summary_text).like(pattern),
                func.lower(SummaryRequest.input_text).like(pattern),
            )
            base = base.where(condition)
            count_stmt = count_stmt.where(condition)

        total = int(self.db.execute(count_stmt).scalar_one())
        stmt = (
            base.options(joinedload(Summary.request).joinedload(SummaryRequest.document))
            .order_by(Summary.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.execute(stmt).unique().scalars()), total

    def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Summary)
            .join(SummaryRequest, Summary.request_id == SummaryRequest.id)
            .where(SummaryRequest.user_id == user_id)
        )
        return int(self.db.execute(stmt).scalar_one())

    def average_processing_time(self) -> float:
        stmt = select(func.avg(Summary.processing_time_seconds))
        return float(self.db.execute(stmt).scalar() or 0.0)

    def total_words_summarized(self) -> int:
        stmt = select(func.sum(SummaryRequest.input_word_count))
        return int(self.db.execute(stmt).scalar() or 0)
