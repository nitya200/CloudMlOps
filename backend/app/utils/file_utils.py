"""Filesystem and byte-level helpers for uploads."""

from __future__ import annotations

import codecs
import re
import unicodedata
import uuid
from pathlib import Path

# Magic byte prefixes used to verify that the bytes match the claimed
# extension. A trusting `.pdf` check alone is easy to bypass.
MAGIC_PREFIXES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF-",),
    # DOCX is a ZIP container; the trailing variants cover empty/spanned archives.
    "docx": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".")


def sanitize_filename(filename: str, *, max_length: int = 120) -> str:
    """Strip directory components and unsafe characters from a client filename.

    Prevents path traversal (``../../etc/passwd``) and odd unicode in the name
    from ever reaching the filesystem.
    """
    base = Path(filename.replace("\\", "/")).name
    normalized = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode("ascii")
    cleaned = _UNSAFE_CHARS.sub("_", normalized).strip("._-")
    if not cleaned:
        cleaned = "upload"
    stem = Path(cleaned).stem[:max_length]
    suffix = Path(cleaned).suffix[:10]
    return f"{stem}{suffix}"


def unique_storage_name(filename: str) -> str:
    """Prefix a short random token so concurrent uploads never collide."""
    return f"{uuid.uuid4().hex[:12]}_{sanitize_filename(filename)}"


def matches_magic_bytes(extension: str, data: bytes) -> bool:
    prefixes = MAGIC_PREFIXES.get(extension)
    if not prefixes:
        return True  # plain text has no signature to check
    return any(data.startswith(prefix) for prefix in prefixes)


def looks_like_text(data: bytes) -> bool:
    """Reject binary payloads uploaded with a .txt extension."""
    if b"\x00" in data[:4096]:
        return False
    try:
        data[:4096].decode("utf-8")
    except UnicodeDecodeError:
        try:
            data[:4096].decode("latin-1")
        except UnicodeDecodeError:
            return False
    return True


def decode_text(data: bytes) -> str:
    """Decode text bytes, trying the encodings real-world uploads use.

    UTF-16 is only attempted when a byte order mark says so: without that
    guard, single-byte Latin text decodes "successfully" into CJK gibberish.
    """
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        try:
            return data.decode("utf-16")
        except UnicodeDecodeError:
            pass
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return data.decode("utf-8", errors="replace")


def write_bytes(destination: Path, data: bytes) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return destination
