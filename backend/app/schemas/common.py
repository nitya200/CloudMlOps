"""Reusable response envelopes."""

from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ItemT = TypeVar("ItemT")


class Page(BaseModel, Generic[ItemT]):
    """Standard pagination envelope used by every list endpoint."""

    items: list[ItemT]
    total: int = Field(description="Total matching rows, ignoring pagination")
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    pages: int = Field(description="Total number of pages")

    @classmethod
    def build(cls, items: list[ItemT], *, total: int, page: int, page_size: int) -> Page[ItemT]:
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=max(1, ceil(total / page_size)) if total else 0,
        )


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    code: str = Field(examples=["not_found"])
    message: str = Field(examples=["Summary not found."])
    details: dict = Field(default_factory=dict)
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    environment: str
    version: str
    database: str = Field(description="'connected' or an error label")
    ai_backend: str
    ai_model: str
    model_loaded: bool
