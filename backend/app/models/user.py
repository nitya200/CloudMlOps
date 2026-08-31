"""User entity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.feedback import FeedbackRecord
    from app.models.session import Session
    from app.models.summary_request import SummaryRequest
    from app.models.usage_metric import UsageMetric


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        enum_column(UserRole, name="user_role", length=20),
        nullable=False,
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    sessions: Mapped[list[Session]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    summary_requests: Mapped[list[SummaryRequest]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    feedback_records: Mapped[list[FeedbackRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    usage_metrics: Mapped[list[UsageMetric]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"
