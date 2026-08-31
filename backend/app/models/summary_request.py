"""SummaryRequest entity - the audit record of what the user asked for."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import RequestStatus, SourceType, SummaryLength

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.summary import Summary
    from app.models.user import User


class SummaryRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "summary_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_type: Mapped[SourceType] = mapped_column(
        enum_column(SourceType, name="source_type", length=20),
        nullable=False,
    )
    summary_length: Mapped[SummaryLength] = mapped_column(
        enum_column(SummaryLength, name="summary_length", length=20),
        nullable=False,
        default=SummaryLength.MEDIUM,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled")
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[RequestStatus] = mapped_column(
        enum_column(RequestStatus, name="request_status", length=20),
        nullable=False,
        default=RequestStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    user: Mapped[User] = relationship(back_populates="summary_requests")
    document: Mapped[Document | None] = relationship(back_populates="summary_requests")
    summary: Mapped[Summary | None] = relationship(
        back_populates="request", cascade="all, delete-orphan", uselist=False
    )
