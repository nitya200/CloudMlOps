"""Persistence and aggregation for usage telemetry."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.models import MetricType, UsageMetric
from app.repositories.base import BaseRepository


class MetricRepository(BaseRepository[UsageMetric]):
    model = UsageMetric

    def record(
        self,
        *,
        user_id: uuid.UUID | None,
        metric_type: MetricType,
        success: bool = True,
        duration_seconds: float = 0.0,
        detail: str | None = None,
        attributes: dict | None = None,
    ) -> UsageMetric:
        return self.create(
            user_id=user_id,
            metric_type=metric_type,
            success=success,
            duration_seconds=duration_seconds,
            detail=detail,
            attributes=attributes,
        )

    def counts_by_type(self) -> dict[str, int]:
        stmt = select(UsageMetric.metric_type, func.count()).group_by(UsageMetric.metric_type)
        return {str(metric_type): int(count) for metric_type, count in self.db.execute(stmt)}

    def failure_count(self) -> int:
        stmt = select(func.count()).select_from(UsageMetric).where(UsageMetric.success.is_(False))
        return int(self.db.execute(stmt).scalar_one())

    def daily_activity(self, days: int = 14) -> list[dict[str, object]]:
        """Requests per day, oldest first, for the admin dashboard chart."""
        since = datetime.now(UTC) - timedelta(days=days)
        day = func.date(UsageMetric.created_at)
        stmt = (
            select(day.label("day"), func.count().label("total"))
            .where(UsageMetric.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
        return [{"day": str(row.day), "total": int(row.total)} for row in self.db.execute(stmt)]

    def list_recent(self, *, limit: int = 50, offset: int = 0) -> tuple[list[UsageMetric], int]:
        total = self.count()
        stmt = (
            select(UsageMetric).order_by(UsageMetric.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.db.execute(stmt).scalars()), total
