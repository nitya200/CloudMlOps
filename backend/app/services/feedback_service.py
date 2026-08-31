"""Summary quality feedback (UC-13 Rate summary)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.models import FeedbackRecord, MetricType, User
from app.repositories import FeedbackRepository, MetricRepository, SummaryRepository
from app.schemas.feedback import FeedbackRequest

logger = get_logger(__name__)


class FeedbackService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.feedback = FeedbackRepository(db)
        self.summaries = SummaryRepository(db)
        self.metrics = MetricRepository(db)

    def submit(self, user: User, payload: FeedbackRequest) -> FeedbackRecord:
        if not 1 <= payload.rating <= 5:  # defence in depth behind the schema
            raise ValidationError("Rating must be between 1 and 5.")

        # Ownership check doubles as the existence check: a user may only rate
        # a summary they generated.
        summary = self.summaries.get_for_user(payload.summary_id, user.id)
        if summary is None:
            raise NotFoundError("Summary not found.")

        record = self.feedback.get_by_summary_and_user(summary.id, user.id)
        if record is None:
            record = self.feedback.create(
                summary_id=summary.id,
                user_id=user.id,
                rating=payload.rating,
                comment=payload.comment,
            )
            action = "created"
        else:
            record.rating = payload.rating
            record.comment = payload.comment
            action = "updated"

        self.metrics.record(
            user_id=user.id,
            metric_type=MetricType.FEEDBACK,
            detail=f"rating={payload.rating}",
            attributes={"summary_id": str(summary.id), "action": action},
        )
        self.db.commit()
        logger.info(
            "feedback recorded",
            extra={"summary_id": str(summary.id), "rating": payload.rating, "action": action},
        )
        return record

    def list_for_summary(self, user: User, summary_id: str) -> list[FeedbackRecord]:
        summary = self.summaries.get_for_user(summary_id, user.id)
        if summary is None:
            raise NotFoundError("Summary not found.")
        return self.feedback.list_for_summary(summary.id)
