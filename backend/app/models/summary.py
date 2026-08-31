"""Summary entity - the AI generated output."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.feedback import FeedbackRecord
    from app.models.summary_request import SummaryRequest


class Summary(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summaries"

    request_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("summary_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    compression_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    processing_time_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    model_name: Mapped[str] = mapped_column(String(120), nullable=False, default="unknown")
    backend: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    request: Mapped[SummaryRequest] = relationship(back_populates="summary")
    feedback_records: Mapped[list[FeedbackRecord]] = relationship(
        back_populates="summary", cascade="all, delete-orphan"
    )
