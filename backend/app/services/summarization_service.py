"""Summarization orchestration (UC-06/07 Generate summary, select length)."""

from __future__ import annotations

import time
import uuid

from sqlalchemy.orm import Session

from app.ai.base import Summarizer
from app.ai.factory import get_summarizer
from app.ai.prompts import SummaryStrategyFactory
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models import (
    Document,
    MetricType,
    RequestStatus,
    SourceType,
    Summary,
    SummaryLength,
    SummaryRequest,
    User,
)
from app.repositories import (
    DocumentRepository,
    MetricRepository,
    SummaryRepository,
    SummaryRequestRepository,
)
from app.schemas.summary import MIN_INPUT_CHARS
from app.utils.text_utils import normalize_text, word_count

logger = get_logger(__name__)


class SummarizationService:
    """Turns a user request into a persisted summary plus telemetry."""

    def __init__(self, db: Session, summarizer: Summarizer | None = None) -> None:
        self.db = db
        self.requests = SummaryRequestRepository(db)
        self.summaries = SummaryRepository(db)
        self.documents = DocumentRepository(db)
        self.metrics = MetricRepository(db)
        # Injected in tests; resolved from the factory in production.
        self._summarizer = summarizer

    @property
    def summarizer(self) -> Summarizer:
        if self._summarizer is None:
            self._summarizer = get_summarizer()
        return self._summarizer

    # ---- public API -------------------------------------------------------
    def summarize_text(
        self,
        user: User,
        *,
        text: str,
        summary_length: SummaryLength = SummaryLength.MEDIUM,
        title: str | None = None,
    ) -> Summary:
        cleaned = self._validate_input(text)
        request = self.requests.create(
            user_id=user.id,
            document_id=None,
            source_type=SourceType.TEXT,
            summary_length=summary_length,
            title=(title or self._derive_title(cleaned))[:255],
            input_text=cleaned,
            input_word_count=word_count(cleaned),
            status=RequestStatus.PENDING,
        )
        return self._run(user, request, MetricType.TEXT_SUMMARIZATION)

    def summarize_document(
        self,
        user: User,
        document_id: uuid.UUID | str,
        *,
        summary_length: SummaryLength = SummaryLength.MEDIUM,
        title: str | None = None,
    ) -> Summary:
        document = self.documents.get_for_user(document_id, user.id)
        if document is None:
            raise NotFoundError("Document not found.")
        cleaned = self._validate_input(document.extracted_text, source=document)
        request = self.requests.create(
            user_id=user.id,
            document_id=document.id,
            source_type=SourceType.DOCUMENT,
            summary_length=summary_length,
            title=(title or document.filename)[:255],
            input_text=cleaned,
            input_word_count=word_count(cleaned),
            status=RequestStatus.PENDING,
        )
        return self._run(user, request, MetricType.DOCUMENT_SUMMARIZATION)

    def get_owned_summary(self, user: User, summary_id: uuid.UUID | str) -> Summary:
        summary = self.summaries.get_for_user(summary_id, user.id)
        if summary is None:
            raise NotFoundError("Summary not found.")
        return summary

    def build_download_text(self, summary: Summary) -> str:
        """Plain-text export used by the download endpoint (UC-09)."""
        request = summary.request
        source = request.document.filename if request.document else "Pasted text"
        return "\n".join(
            [
                "CloudMLOps - AI Document Summary",
                "=" * 60,
                f"Title            : {request.title}",
                f"Source           : {source}",
                f"Summary length   : {request.summary_length}",
                f"Generated at     : {summary.created_at:%Y-%m-%d %H:%M:%S} UTC",
                f"Model            : {summary.model_name} ({summary.backend})",
                f"Processing time  : {summary.processing_time_seconds:.2f}s",
                f"Original words   : {request.input_word_count}",
                f"Summary words    : {summary.word_count}",
                f"Compression      : {summary.compression_ratio:.1%} of the original",
                "=" * 60,
                "",
                "SUMMARY",
                "-" * 60,
                summary.summary_text,
                "",
            ]
        )

    # ---- internals --------------------------------------------------------
    def _run(self, user: User, request: SummaryRequest, metric_type: MetricType) -> Summary:
        strategy = SummaryStrategyFactory.create(request.summary_length)
        started = time.perf_counter()
        try:
            output = self.summarizer.summarize(request.input_text, strategy)
        except Exception as exc:
            elapsed = time.perf_counter() - started
            request.status = RequestStatus.FAILED
            request.error_message = str(exc)[:500]
            self.metrics.record(
                user_id=user.id,
                metric_type=metric_type,
                success=False,
                duration_seconds=elapsed,
                detail=str(exc)[:500],
                attributes={"summary_length": str(request.summary_length)},
            )
            self.db.commit()
            logger.error(
                "summarization failed",
                extra={"summary_request_id": str(request.id), "error": str(exc)},
            )
            raise

        elapsed = time.perf_counter() - started
        summary_words = word_count(output.summary_text)
        ratio = summary_words / request.input_word_count if request.input_word_count else 0.0

        summary = self.summaries.create(
            request_id=request.id,
            summary_text=output.summary_text,
            word_count=summary_words,
            compression_ratio=round(ratio, 4),
            processing_time_seconds=round(elapsed, 3),
            model_name=output.model_name,
            backend=output.backend,
            chunk_count=output.chunk_count,
        )
        request.status = RequestStatus.COMPLETED
        self.metrics.record(
            user_id=user.id,
            metric_type=metric_type,
            success=True,
            duration_seconds=round(elapsed, 3),
            attributes={
                "summary_length": str(request.summary_length),
                "backend": output.backend,
                "input_words": request.input_word_count,
                "summary_words": summary_words,
                "chunks": output.chunk_count,
            },
        )
        self.db.commit()
        logger.info(
            "summary generated",
            extra={
                "summary_id": str(summary.id),
                "user_id": str(user.id),
                "backend": output.backend,
                "seconds": round(elapsed, 3),
            },
        )
        return summary

    @staticmethod
    def _validate_input(text: str, *, source: Document | None = None) -> str:
        cleaned = normalize_text(text or "")
        if not cleaned:
            raise ValidationError(
                "The document contains no readable text to summarize."
                if source
                else "Text cannot be empty."
            )
        if len(cleaned) < MIN_INPUT_CHARS:
            raise ValidationError(
                f"At least {MIN_INPUT_CHARS} characters of text are required to "
                f"produce a meaningful summary (received {len(cleaned)})."
            )
        return cleaned

    @staticmethod
    def _derive_title(text: str) -> str:
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Untitled")
        words = first_line.split()
        title = " ".join(words[:10])
        return (title + "\u2026") if len(words) > 10 else (title or "Untitled")
