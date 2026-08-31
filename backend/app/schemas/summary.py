"""Summarization contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import SourceType, SummaryLength

MIN_INPUT_CHARS = 200


class TextSummaryRequest(BaseModel):
    text: str = Field(
        min_length=MIN_INPUT_CHARS,
        description=f"Raw text to summarize (at least {MIN_INPUT_CHARS} characters).",
        examples=[
            "Artificial intelligence is transforming how organizations process documents. " * 6
        ],
    )
    summary_length: SummaryLength = SummaryLength.MEDIUM
    title: str | None = Field(default=None, max_length=255)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Text cannot be empty.")
        return value


class DocumentSummaryRequest(BaseModel):
    summary_length: SummaryLength = SummaryLength.MEDIUM
    title: str | None = Field(default=None, max_length=255)


class SummaryResponse(BaseModel):
    # ``model_name`` collides with Pydantic's protected "model_" namespace.
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    request_id: uuid.UUID
    summary_text: str
    word_count: int
    compression_ratio: float
    processing_time_seconds: float
    model_name: str
    backend: str
    chunk_count: int
    created_at: datetime


class SummaryDetailResponse(SummaryResponse):
    title: str
    summary_length: SummaryLength
    source_type: SourceType
    document_id: uuid.UUID | None = None
    document_filename: str | None = None
    input_word_count: int
    input_preview: str
    my_rating: int | None = Field(default=None, description="Current user's rating, if any")


class HistoryItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    summary_length: SummaryLength
    source_type: SourceType
    document_filename: str | None = None
    summary_preview: str
    word_count: int
    input_word_count: int
    processing_time_seconds: float
    my_rating: int | None = None
    created_at: datetime
