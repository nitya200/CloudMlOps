"""Registered summarizer versions and their evaluation metrics (UC-12)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    GUID,
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    enum_column,
)
from app.models.enums import ModelVersionStatus, TrainingJobStatus


class ModelVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_versions"

    version_label: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    base_model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    backend: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[ModelVersionStatus] = mapped_column(
        enum_column(ModelVersionStatus, name="model_version_status", length=32),
        nullable=False,
        default=ModelVersionStatus.DRAFT,
    )
    rouge_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    rouge_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    rouge_l: Mapped[float | None] = mapped_column(Float, nullable=True)
    evaluation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    promoted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    training_jobs: Mapped[list[TrainingJob]] = relationship(
        "TrainingJob", back_populates="model_version"
    )


class TrainingJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fine-tuning / re-evaluation pipeline trigger (UC-16)."""

    __tablename__ = "training_jobs"

    status: Mapped[TrainingJobStatus] = mapped_column(
        enum_column(TrainingJobStatus, name="training_job_status", length=20),
        nullable=False,
    )
    triggered_by_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True
    )
    progress_message: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    model_version: Mapped[ModelVersion | None] = relationship(
        "ModelVersion", back_populates="training_jobs"
    )


__all__ = ["ModelVersion", "TrainingJob"]
