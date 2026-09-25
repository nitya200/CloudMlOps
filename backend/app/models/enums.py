"""Enumerations shared by the data and business tiers."""

from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"


class SummaryLength(StrEnum):
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class SummaryStyle(StrEnum):
    """User-facing summarization mode (proposal UC-5)."""

    CONCISE = "concise"
    ABSTRACTIVE = "abstractive"


class SourceType(StrEnum):
    """Where the text being summarized came from."""

    TEXT = "text"
    DOCUMENT = "document"


class FileType(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class RequestStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelVersionStatus(StrEnum):
    DRAFT = "draft"
    EVALUATING = "evaluating"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    RETIRED = "retired"
    FAILED = "failed"


class TrainingJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MetricType(StrEnum):
    LOGIN = "login"
    REGISTRATION = "registration"
    DOCUMENT_UPLOAD = "document_upload"
    TEXT_SUMMARIZATION = "text_summarization"
    DOCUMENT_SUMMARIZATION = "document_summarization"
    SUMMARY_DOWNLOAD = "summary_download"
    FEEDBACK = "feedback"
