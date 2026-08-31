"""Persistence for summary quality feedback."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models import FeedbackRecord
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[FeedbackRecord]):
    model = FeedbackRecord

    def get_by_summary_and_user(
        self, summary_id: uuid.UUID, user_id: uuid.UUID
    ) -> FeedbackRecord | None:
        stmt = select(FeedbackRecord).where(
            FeedbackRecord.summary_id == summary_id, FeedbackRecord.user_id == user_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_summary(self, summary_id: uuid.UUID) -> list[FeedbackRecord]:
        stmt = (
            select(FeedbackRecord)
            .where(FeedbackRecord.summary_id == summary_id)
            .order_by(FeedbackRecord.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars())

    def average_rating(self) -> float:
        stmt = select(func.avg(FeedbackRecord.rating))
        return float(self.db.execute(stmt).scalar() or 0.0)

    def rating_distribution(self) -> dict[int, int]:
        stmt = select(FeedbackRecord.rating, func.count()).group_by(FeedbackRecord.rating)
        counts = {int(rating): int(count) for rating, count in self.db.execute(stmt)}
        return {star: counts.get(star, 0) for star in range(1, 6)}
