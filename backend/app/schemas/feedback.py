"""Feedback contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackRequest(BaseModel):
    summary_id: uuid.UUID
    rating: int = Field(ge=1, le=5, description="Quality rating from 1 (poor) to 5 (excellent)")
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("comment")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    summary_id: uuid.UUID
    rating: int
    comment: str | None
    created_at: datetime
