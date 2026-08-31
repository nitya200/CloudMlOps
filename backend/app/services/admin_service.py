"""Administrator reporting and user management (UC-14/15/16)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models import Document, RequestStatus, User, UserRole
from app.repositories import (
    DocumentRepository,
    FeedbackRepository,
    MetricRepository,
    SessionRepository,
    SummaryRepository,
    SummaryRequestRepository,
    UserRepository,
)
from app.schemas.admin import (
    PlatformStatsResponse,
    QualityMetricsResponse,
    UsageMetricsResponse,
)

logger = get_logger(__name__)


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.documents = DocumentRepository(db)
        self.requests = SummaryRequestRepository(db)
        self.summaries = SummaryRepository(db)
        self.feedback = FeedbackRepository(db)
        self.metrics = MetricRepository(db)

    # ---- users ------------------------------------------------------------
    def list_users(
        self,
        *,
        search: str | None = None,
        role: UserRole | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[User], int]:
        return self.users.list_users(search=search, role=role, limit=limit, offset=offset)

    def set_active(self, admin: User, user_id: uuid.UUID | str, is_active: bool) -> User:
        user = self._get_user(user_id)
        if user.id == admin.id and not is_active:
            # Locking yourself out would leave the platform unmanageable.
            raise ConflictError("You cannot deactivate your own administrator account.")
        user.is_active = is_active
        if not is_active:
            # Revoke live sessions immediately; otherwise an existing JWT would
            # keep working until it expired.
            self.sessions.revoke_all_for_user(user.id)
        self.db.commit()
        logger.info(
            "user activation changed",
            extra={"target_user": str(user.id), "is_active": is_active, "by": str(admin.id)},
        )
        return user

    def set_role(self, admin: User, user_id: uuid.UUID | str, role: UserRole) -> User:
        user = self._get_user(user_id)
        if user.id == admin.id and role != UserRole.ADMIN:
            raise ConflictError("You cannot remove your own administrator role.")
        user.role = role
        self.sessions.revoke_all_for_user(user.id)  # force a token with the new claim
        self.db.commit()
        logger.info("user role changed", extra={"target_user": str(user.id), "role": str(role)})
        return user

    def _get_user(self, user_id: uuid.UUID | str) -> User:
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    # ---- reporting --------------------------------------------------------
    def platform_stats(self) -> PlatformStatsResponse:
        total_requests = self.requests.count()
        return PlatformStatsResponse(
            total_users=self.users.count(),
            active_users=self.users.count_active(),
            total_documents=DocumentRepository(self.db).count(),
            total_requests=total_requests,
            total_summaries=self.summaries.count(),
            failed_requests=self.requests.count_by_status(RequestStatus.FAILED),
            average_processing_time_seconds=round(self.summaries.average_processing_time(), 3),
            average_rating=round(self.feedback.average_rating(), 2),
            total_feedback=self.feedback.count(),
            total_words_summarized=self.summaries.total_words_summarized(),
        )

    def usage_metrics(self, *, days: int = 14) -> UsageMetricsResponse:
        return UsageMetricsResponse(
            counts_by_type=self.metrics.counts_by_type(),
            failures=self.metrics.failure_count(),
            daily_activity=self.metrics.daily_activity(days=days),
        )

    def quality_metrics(self) -> QualityMetricsResponse:
        total_requests = self.requests.count()
        completed = self.requests.count_by_status(RequestStatus.COMPLETED)
        success_rate = (completed / total_requests * 100) if total_requests else 0.0
        return QualityMetricsResponse(
            average_rating=round(self.feedback.average_rating(), 2),
            total_feedback=self.feedback.count(),
            rating_distribution=self.feedback.rating_distribution(),
            success_rate=round(success_rate, 2),
        )


__all__ = ["AdminService", "Document"]
