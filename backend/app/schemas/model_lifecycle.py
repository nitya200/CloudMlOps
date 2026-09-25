"""Model registry and training job API contracts (UC-12 / UC-16)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import ModelVersionStatus, TrainingJobStatus


class ModelVersionResponse(BaseModel):
    id: UUID
    version_label: str
    base_model_name: str
    backend: str
    status: ModelVersionStatus
    rouge_1: float | None = None
    rouge_2: float | None = None
    rouge_l: float | None = None
    evaluation_notes: str | None = None
    approved_at: datetime | None = None
    promoted_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingJobResponse(BaseModel):
    id: UUID
    status: TrainingJobStatus
    model_version_id: UUID | None = None
    progress_message: str
    error_message: str | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TrainingJobCreate(BaseModel):
    notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional note stored on the registered model version.",
    )
