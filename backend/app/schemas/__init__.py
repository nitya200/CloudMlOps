"""Pydantic contracts shared between the API layer and the frontend."""

from app.schemas.admin import (
    PlatformStatsResponse,
    QualityMetricsResponse,
    UsageMetricsResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import ErrorResponse, HealthResponse, MessageResponse, Page
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.summary import (
    DocumentSummaryRequest,
    HistoryItemResponse,
    SummaryDetailResponse,
    SummaryResponse,
    TextSummaryRequest,
)

__all__ = [
    "DocumentDetailResponse",
    "DocumentResponse",
    "DocumentSummaryRequest",
    "DocumentUploadResponse",
    "ErrorResponse",
    "FeedbackRequest",
    "FeedbackResponse",
    "HealthResponse",
    "HistoryItemResponse",
    "LoginRequest",
    "MessageResponse",
    "Page",
    "PlatformStatsResponse",
    "QualityMetricsResponse",
    "RegisterRequest",
    "SummaryDetailResponse",
    "SummaryResponse",
    "TextSummaryRequest",
    "TokenResponse",
    "UsageMetricsResponse",
    "UserResponse",
    "UserRoleUpdate",
    "UserStatusUpdate",
]
