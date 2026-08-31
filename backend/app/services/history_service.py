"""Summary history (UC-10 view, UC-11 search, UC-12 delete)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models import Summary, User
from app.repositories import FeedbackRepository, SummaryRepository
from app.schemas.summary import HistoryItemResponse, SummaryDetailResponse
from app.utils.text_utils import preview

logger = get_logger(__name__)


class HistoryService:
    """Read model over a user's own summaries."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.summaries = SummaryRepository(db)
        self.feedback = FeedbackRepository(db)

    def list_history(
        self,
        user: User,
        *,
        search: str | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[HistoryItemResponse], int]:
        rows, total = self.summaries.search_history(
            user.id, search=search, limit=limit, offset=offset
        )
        items = [self._to_history_item(summary, user) for summary in rows]
        return items, total

    def get_detail(self, user: User, summary_id: uuid.UUID | str) -> SummaryDetailResponse:
        summary = self.summaries.get_for_user(summary_id, user.id)
        if summary is None:
            raise NotFoundError("Summary not found.")
        return self._to_detail(summary, user)

    def delete(self, user: User, summary_id: uuid.UUID | str) -> None:
        summary = self.summaries.get_for_user(summary_id, user.id)
        if summary is None:
            raise NotFoundError("Summary not found.")
        # Deleting the request cascades to the summary and its feedback, so the
        # history entry disappears completely rather than leaving an orphan.
        self.db.delete(summary.request)
        self.db.commit()
        logger.info("summary deleted", extra={"summary_id": str(summary_id)})

    # ---- mapping ----------------------------------------------------------
    def _my_rating(self, summary: Summary, user: User) -> int | None:
        record = self.feedback.get_by_summary_and_user(summary.id, user.id)
        return record.rating if record else None

    def _to_history_item(self, summary: Summary, user: User) -> HistoryItemResponse:
        request = summary.request
        return HistoryItemResponse(
            id=summary.id,
            title=request.title,
            summary_length=request.summary_length,
            source_type=request.source_type,
            document_filename=request.document.filename if request.document else None,
            summary_preview=preview(summary.summary_text, 260),
            word_count=summary.word_count,
            input_word_count=request.input_word_count,
            processing_time_seconds=summary.processing_time_seconds,
            my_rating=self._my_rating(summary, user),
            created_at=summary.created_at,
        )

    def _to_detail(self, summary: Summary, user: User) -> SummaryDetailResponse:
        request = summary.request
        return SummaryDetailResponse(
            id=summary.id,
            request_id=summary.request_id,
            summary_text=summary.summary_text,
            word_count=summary.word_count,
            compression_ratio=summary.compression_ratio,
            processing_time_seconds=summary.processing_time_seconds,
            model_name=summary.model_name,
            backend=summary.backend,
            chunk_count=summary.chunk_count,
            created_at=summary.created_at,
            title=request.title,
            summary_length=request.summary_length,
            source_type=request.source_type,
            document_id=request.document_id,
            document_filename=request.document.filename if request.document else None,
            input_word_count=request.input_word_count,
            input_preview=preview(request.input_text, 600),
            my_rating=self._my_rating(summary, user),
        )
