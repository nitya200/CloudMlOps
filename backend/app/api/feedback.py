"""Feedback endpoints (UC-13 Rate summary quality)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Rate a summary from 1 to 5 stars",
    responses={
        404: {"description": "Summary not found or not owned by the caller"},
        422: {"description": "Rating outside the 1-5 range"},
    },
)
def submit_feedback(
    payload: FeedbackRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> FeedbackResponse:
    """Create or update the caller's rating for one of their own summaries."""
    record = FeedbackService(db).submit(current_user, payload)
    return FeedbackResponse.model_validate(record)


@router.get(
    "/summary/{summary_id}",
    response_model=list[FeedbackResponse],
    summary="List the feedback recorded for a summary",
    responses={404: {"description": "Summary not found or not owned by the caller"}},
)
def list_feedback(
    summary_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> list[FeedbackResponse]:
    records = FeedbackService(db).list_for_summary(current_user, summary_id)
    return [FeedbackResponse.model_validate(record) for record in records]
