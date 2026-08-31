"""Administrator dashboard contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserRoleUpdate(BaseModel):
    role: UserRole


class PlatformStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_documents: int
    total_requests: int
    total_summaries: int
    failed_requests: int
    average_processing_time_seconds: float
    average_rating: float = Field(description="Mean of all 1-5 star ratings, 0 when none")
    total_feedback: int
    total_words_summarized: int


class UsageMetricsResponse(BaseModel):
    counts_by_type: dict[str, int]
    failures: int
    daily_activity: list[dict]


class QualityMetricsResponse(BaseModel):
    average_rating: float
    total_feedback: int
    rating_distribution: dict[int, int]
    success_rate: float = Field(description="Completed requests / all requests, as a percentage")
