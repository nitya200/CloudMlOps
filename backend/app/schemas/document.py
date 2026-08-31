"""Document upload contracts."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FileType


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_type: FileType
    size_bytes: int
    page_count: int | None
    word_count: int
    created_at: datetime


class DocumentUploadResponse(DocumentResponse):
    extracted_characters: int = Field(description="Length of the extracted text")
    text_preview: str = Field(description="First 500 characters of the extracted text")


class DocumentDetailResponse(DocumentResponse):
    extracted_text: str
