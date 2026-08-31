"""History endpoints (UC-10 View, UC-11 Search, UC-12 Delete)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession, Pagination
from app.schemas.common import MessageResponse, Page
from app.schemas.summary import HistoryItemResponse, SummaryDetailResponse
from app.services.history_service import HistoryService

router = APIRouter(prefix="/history", tags=["History"])


@router.get(
    "",
    response_model=Page[HistoryItemResponse],
    summary="List the current user's summaries, newest first",
)
def list_history(
    current_user: CurrentUser,
    db: DbSession,
    pagination: Pagination,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Filter by title, summary or original text"),
    ] = None,
) -> Page[HistoryItemResponse]:
    """Paginated, optionally filtered history scoped to the authenticated user."""
    items, total = HistoryService(db).list_history(
        current_user, search=search, limit=pagination.limit, offset=pagination.offset
    )
    return Page.build(items, total=total, page=pagination.page, page_size=pagination.page_size)


@router.get(
    "/{summary_id}",
    response_model=SummaryDetailResponse,
    summary="Get one history entry",
    responses={404: {"description": "Summary not found or not owned by the caller"}},
)
def get_history_item(
    summary_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SummaryDetailResponse:
    return HistoryService(db).get_detail(current_user, summary_id)


@router.delete(
    "/{summary_id}",
    response_model=MessageResponse,
    summary="Delete a summary from the history",
    responses={404: {"description": "Summary not found or not owned by the caller"}},
)
def delete_history_item(
    summary_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> MessageResponse:
    HistoryService(db).delete(current_user, summary_id)
    return MessageResponse(message="Summary deleted.")
