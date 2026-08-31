"""ORM entities (data tier).

Importing this package registers every table on ``Base.metadata``.
"""

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.document import Document
from app.models.enums import (
    FileType,
    MetricType,
    RequestStatus,
    SourceType,
    SummaryLength,
    UserRole,
)
from app.models.feedback import FeedbackRecord
from app.models.session import Session
from app.models.summary import Summary
from app.models.summary_request import SummaryRequest
from app.models.usage_metric import UsageMetric
from app.models.user import User

__all__ = [
    "GUID",
    "Base",
    "Document",
    "FeedbackRecord",
    "FileType",
    "MetricType",
    "RequestStatus",
    "Session",
    "SourceType",
    "Summary",
    "SummaryLength",
    "SummaryRequest",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "UsageMetric",
    "User",
    "UserRole",
]
