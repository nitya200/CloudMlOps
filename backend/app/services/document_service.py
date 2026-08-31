"""Document upload, retrieval and deletion business logic."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Document, MetricType, User
from app.repositories import DocumentRepository, MetricRepository
from app.services.extraction_service import ExtractionService
from app.services.storage import StorageBackend, get_storage
from app.utils.file_utils import get_extension, unique_storage_name
from app.utils.validators import validate_content_type, validate_upload

logger = get_logger(__name__)


class DocumentService:
    """UC-05 Upload document, plus document reads and deletes."""

    def __init__(
        self,
        db: Session,
        extraction_service: ExtractionService | None = None,
        storage: StorageBackend | None = None,
    ) -> None:
        self.db = db
        self.documents = DocumentRepository(db)
        self.metrics = MetricRepository(db)
        # Injected so tests can substitute a stub extractor.
        self.extraction = extraction_service or ExtractionService()
        self._storage = storage

    @property
    def storage(self) -> StorageBackend:
        if self._storage is None:
            self._storage = get_storage()
        return self._storage

    def upload(
        self,
        user: User,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
        persist_file: bool = True,
    ) -> Document:
        started = time.perf_counter()
        try:
            file_type = validate_upload(filename, content_type, data)
            result = self.extraction.extract(file_type, data)
        except Exception as exc:
            self.metrics.record(
                user_id=user.id,
                metric_type=MetricType.DOCUMENT_UPLOAD,
                success=False,
                duration_seconds=time.perf_counter() - started,
                detail=str(exc)[:500],
                attributes={"extension": get_extension(filename)},
            )
            self.db.commit()
            raise

        storage_path: str | None = None
        if persist_file:
            # A backend-relative key, not an absolute path: the same value is a
            # filesystem path under STORAGE_DIR or an S3 object key.
            key = f"{user.id}/{unique_storage_name(filename)}"
            storage_path = self.storage.save(key, data)

        document = self.documents.create(
            user_id=user.id,
            filename=Path(filename).name[:255],
            file_type=file_type,
            storage_path=storage_path,
            size_bytes=len(data),
            page_count=result.page_count,
            word_count=result.word_count,
            extracted_text=result.text,
        )
        self.metrics.record(
            user_id=user.id,
            metric_type=MetricType.DOCUMENT_UPLOAD,
            success=True,
            duration_seconds=time.perf_counter() - started,
            attributes={
                "file_type": str(file_type),
                "size_bytes": len(data),
                "word_count": result.word_count,
                "declared_content_type_ok": validate_content_type(str(file_type), content_type),
            },
        )
        self.db.commit()
        logger.info(
            "document uploaded",
            extra={
                "document_id": str(document.id),
                "user_id": str(user.id),
                "file_type": str(file_type),
                "words": result.word_count,
            },
        )
        return document

    def get_owned(self, user: User, document_id: uuid.UUID | str) -> Document:
        document = self.documents.get_for_user(document_id, user.id)
        if document is None:
            raise NotFoundError("Document not found.")
        return document

    def list_for_user(self, user: User, *, limit: int, offset: int) -> tuple[list[Document], int]:
        return self.documents.list_for_user(user.id, limit=limit, offset=offset)

    def delete(self, user: User, document_id: uuid.UUID | str) -> None:
        document = self.get_owned(user, document_id)
        if document.storage_path:
            try:
                self.storage.delete(document.storage_path)
            except Exception as exc:
                # An orphaned blob is a cleanup problem, not a reason to leave
                # the user staring at a document they asked to delete.
                logger.warning(
                    "could not delete stored file",
                    extra={"document_id": str(document_id), "error": str(exc)},
                )
        self.documents.delete(document)
        self.db.commit()
        logger.info("document deleted", extra={"document_id": str(document_id)})
