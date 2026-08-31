"""Document entity - an uploaded file plus its extracted text."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import FileType

if TYPE_CHECKING:
    from app.models.summary_request import SummaryRequest
    from app.models.user import User


class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        enum_column(FileType, name="file_type", length=10),
        nullable=False,
    )
    # Local path today, S3 object key once storage moves to AWS.
    storage_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    user: Mapped[User] = relationship(back_populates="documents")
    summary_requests: Mapped[list[SummaryRequest]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    @property
    def character_count(self) -> int:
        return len(self.extracted_text or "")
