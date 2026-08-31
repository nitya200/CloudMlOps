"""Pluggable blob storage for uploaded files.

App Runner instance storage is ephemeral and per instance: a redeploy wipes it,
and with two instances behind one URL, the instance that serves a download is
often not the one that took the upload. Extracted text lives in PostgreSQL so
summaries, history and search are unaffected either way, but the original file
needs somewhere durable.

``STORAGE_BACKEND=local`` keeps the simple filesystem behaviour for development
and Docker Compose; ``STORAGE_BACKEND=s3`` stores objects in a bucket. Both
implement the same tiny interface, so ``DocumentService`` does not know or care
which one is active.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    """Where the bytes of an uploaded document live."""

    name: str

    @abstractmethod
    def save(self, key: str, data: bytes) -> str:
        """Persist ``data`` and return the key needed to read it back."""

    @abstractmethod
    def load(self, key: str) -> bytes | None:
        """Return the stored bytes, or ``None`` when the object is gone."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the object. Must not raise when it is already absent."""


class LocalStorage(StorageBackend):
    """Filesystem storage rooted at ``STORAGE_DIR``."""

    name = "local"

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.storage_path

    def _resolve(self, key: str) -> Path:
        # Defence in depth: the key is generated server side, but a traversal
        # here would let a crafted key escape the storage root.
        target = (self.root / key).resolve()
        root = self.root.resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"Refusing to access {key!r} outside the storage root.")
        return target

    def save(self, key: str, data: bytes) -> str:
        target = self._resolve(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return key

    def load(self, key: str) -> bytes | None:
        target = self._resolve(key)
        return target.read_bytes() if target.is_file() else None

    def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)


class S3Storage(StorageBackend):
    """Amazon S3 storage. Credentials come from the App Runner instance role."""

    name = "s3"

    def __init__(self, bucket: str, prefix: str = "", region: str | None = None) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - exercised by config, not tests
            raise RuntimeError(
                "STORAGE_BACKEND=s3 requires boto3. Install requirements-aws.txt."
            ) from exc

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = boto3.client("s3", region_name=region)

    def _object_key(self, key: str) -> str:
        return f"{self.prefix}/{key}" if self.prefix else key

    def save(self, key: str, data: bytes) -> str:
        self._client.put_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
            Body=data,
            # Belt and braces: the bucket should also enforce this by policy.
            ServerSideEncryption="AES256",
        )
        return key

    def load(self, key: str) -> bytes | None:
        try:
            response = self._client.get_object(Bucket=self.bucket, Key=self._object_key(key))
        except self._client.exceptions.NoSuchKey:
            return None
        return response["Body"].read()

    def delete(self, key: str) -> None:
        # delete_object is idempotent; a missing key is not an error.
        self._client.delete_object(Bucket=self.bucket, Key=self._object_key(key))


def create_storage() -> StorageBackend:
    if settings.storage_backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET to be set.")
        logger.info("using S3 storage", extra={"bucket": settings.s3_bucket})
        return S3Storage(settings.s3_bucket, settings.s3_prefix, settings.s3_region)
    return LocalStorage()


def get_storage() -> StorageBackend:
    """Resolve the configured backend once per process."""
    global _cached
    if _cached is None:
        with _lock:
            if _cached is None:
                _cached = create_storage()
    return _cached


def set_storage(backend: StorageBackend | None) -> None:
    """Override the cached backend. Used by tests; ``None`` restores default."""
    global _cached
    with _lock:
        _cached = backend


_lock = threading.Lock()
_cached: StorageBackend | None = None
