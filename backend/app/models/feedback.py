"""FeedbackRecord entity - user rating of a generated summary."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.summary import Summary
    from app.models.user import User


class FeedbackRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "feedback_records"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
        # One rating per user per summary; re-rating updates the existing row.
        UniqueConstraint("summary_id", "user_id", name="uq_feedback_summary_user"),
    )

    summary_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("summaries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    summary: Mapped[Summary] = relationship(back_populates="feedback_records")
    user: Mapped[User] = relationship(back_populates="feedback_records")
