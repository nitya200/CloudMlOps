"""UsageMetric entity - operational telemetry for the admin dashboard."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import MetricType

if TYPE_CHECKING:
    from app.models.user import User


class UsageMetric(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "usage_metrics"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    metric_type: Mapped[MetricType] = mapped_column(
        enum_column(MetricType, name="metric_type", length=40),
        nullable=False,
        index=True,
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Free-form context (file type, summary length, ...) kept out of columns so
    # new telemetry does not require a migration.
    attributes: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user: Mapped[User | None] = relationship(back_populates="usage_metrics")
