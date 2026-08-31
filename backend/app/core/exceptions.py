"""Domain level exceptions.

Services raise these instead of ``HTTPException`` so the business tier stays
independent of the web framework. ``app.main`` translates them into HTTP
responses in one place.
"""

from __future__ import annotations


class AppError(Exception):
    """Base class for all expected application failures."""

    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class PayloadTooLargeError(AppError):
    status_code = 413
    code = "payload_too_large"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"

    def __init__(self, message: str, *, retry_after: int, details: dict | None = None) -> None:
        super().__init__(message, details=details)
        # Surfaced as the standard Retry-After header by the error handler.
        self.retry_after = retry_after


class UnsupportedFileTypeError(AppError):
    status_code = 415
    code = "unsupported_file_type"


class ExtractionError(AppError):
    status_code = 422
    code = "extraction_failed"


class SummarizationError(AppError):
    status_code = 503
    code = "summarization_failed"
