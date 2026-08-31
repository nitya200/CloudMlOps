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


class MetricType(StrEnum):
    LOGIN = "login"
    REGISTRATION = "registration"
    DOCUMENT_UPLOAD = "document_upload"
    TEXT_SUMMARIZATION = "text_summarization"
    DOCUMENT_SUMMARIZATION = "document_summarization"
    SUMMARY_DOWNLOAD = "summary_download"
    FEEDBACK = "feedback"
