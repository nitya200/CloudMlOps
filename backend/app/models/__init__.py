"""ORM entities (data tier).

Importing this package registers every table on ``Base.metadata``.
"""

from app.models.base import GUID, Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.document import Document
from app.models.email_verification import EmailVerificationToken
from app.models.enums import (
    FileType,
    MetricType,
    ModelVersionStatus,
    RequestStatus,
    SourceType,
    SummaryLength,
    SummaryStyle,
    TrainingJobStatus,
    UserRole,
)
from app.models.model_version import ModelVersion, TrainingJob
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
    "EmailVerificationToken",
    "FeedbackRecord",
    "FileType",
    "MetricType",
    "ModelVersion",
    "ModelVersionStatus",
    "TrainingJob",
    "TrainingJobStatus",
    "RequestStatus",
    "Session",
    "SourceType",
    "Summary",
    "SummaryLength",
    "SummaryStyle",
    "SummaryRequest",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "UsageMetric",
    "User",
    "UserRole",
]
