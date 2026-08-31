"""Upload validation rules."""

from __future__ import annotations

from app.core.config import settings
from app.core.exceptions import (
    PayloadTooLargeError,
    UnsupportedFileTypeError,
    ValidationError,
)
from app.models.enums import FileType
from app.utils.file_utils import get_extension, looks_like_text, matches_magic_bytes

SUPPORTED_EXTENSIONS: tuple[str, ...] = tuple(file_type.value for file_type in FileType)

ALLOWED_CONTENT_TYPES: dict[str, tuple[str, ...]] = {
    "pdf": ("application/pdf", "application/x-pdf"),
    "docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
    ),
    "txt": ("text/plain", "text/markdown", "application/octet-stream"),
}


def validate_upload(filename: str, content_type: str | None, data: bytes) -> FileType:
    """Validate extension, declared MIME type, size and magic bytes.

    Returns the resolved ``FileType`` or raises a domain error.
    """
    if not filename or not filename.strip():
        raise ValidationError("A filename is required.")

    extension = get_extension(filename)
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileTypeError(
            f"Unsupported file type '.{extension or filename}'. "
            f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}.",
            details={"supported": list(SUPPORTED_EXTENSIONS)},
        )

    if not data:
        raise ValidationError("The uploaded file is empty.")

    if len(data) > settings.max_upload_size_bytes:
        raise PayloadTooLargeError(
            f"File is larger than the {settings.max_upload_size_mb} MB limit.",
            details={"max_bytes": settings.max_upload_size_bytes, "actual_bytes": len(data)},
        )

    # The declared MIME type is advisory only - browsers get it wrong - so a
    # mismatch is not fatal, but the magic bytes must agree with the extension.
    if not matches_magic_bytes(extension, data):
        raise UnsupportedFileTypeError(f"File contents do not look like a valid .{extension} file.")
    if extension == "txt" and not looks_like_text(data):
        raise UnsupportedFileTypeError("File contents are binary, not plain text.")

    return FileType(extension)


def validate_content_type(extension: str, content_type: str | None) -> bool:
    """Advisory check used for telemetry rather than rejection."""
    if not content_type:
        return True
    allowed = ALLOWED_CONTENT_TYPES.get(extension, ())
    return content_type.split(";")[0].strip().lower() in allowed
