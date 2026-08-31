"""Summarization endpoints (UC-06 Generate, UC-07 Select length, UC-09 Download)."""

from __future__ import annotations

import time

from fastapi import APIRouter, status
from fastapi.responses import PlainTextResponse

from app.ai.factory import get_summarizer
from app.ai.prompts import SummaryStrategyFactory
from app.api.deps import CurrentUser, DbSession
from app.models import MetricType
from app.repositories import MetricRepository
from app.schemas.summary import (
    DocumentSummaryRequest,
    SummaryDetailResponse,
    SummaryResponse,
    TextSummaryRequest,
)
from app.services.history_service import HistoryService
from app.services.summarization_service import SummarizationService
from app.utils.file_utils import sanitize_filename

router = APIRouter(prefix="/summaries", tags=["Summarization"])


@router.get("/options", summary="List the available summary length options")
def summary_options() -> dict[str, object]:
    summarizer = get_summarizer()
    return {
        "lengths": SummaryStrategyFactory.available(),
        "backend": summarizer.backend,
        "model": summarizer.model_name,
    }


@router.post(
    "/text",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Summarize raw text",
    responses={
        422: {"description": "Text missing or too short to summarize"},
        503: {"description": "The summarization model is unavailable"},
    },
)
def summarize_text(
    payload: TextSummaryRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SummaryResponse:
    """Generate an abstractive summary from pasted text."""
    summary = SummarizationService(db).summarize_text(
        current_user,
        text=payload.text,
        summary_length=payload.summary_length,
        title=payload.title,
    )
    return SummaryResponse.model_validate(summary)


@router.post(
    "/document/{document_id}",
    response_model=SummaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Summarize a previously uploaded document",
    responses={
        404: {"description": "Document not found or not owned by the caller"},
        422: {"description": "Document has no readable text"},
        503: {"description": "The summarization model is unavailable"},
    },
)
def summarize_document(
    document_id: str,
    payload: DocumentSummaryRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> SummaryResponse:
    summary = SummarizationService(db).summarize_document(
        current_user,
        document_id,
        summary_length=payload.summary_length,
        title=payload.title,
    )
    return SummaryResponse.model_validate(summary)


@router.get(
    "/{summary_id}",
    response_model=SummaryDetailResponse,
    summary="Get one summary with its request context",
    responses={404: {"description": "Summary not found or not owned by the caller"}},
)
def get_summary(
    summary_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> SummaryDetailResponse:
    return HistoryService(db).get_detail(current_user, summary_id)


@router.get(
    "/{summary_id}/download",
    response_class=PlainTextResponse,
    summary="Download a summary as a .txt file",
    responses={
        200: {"content": {"text/plain": {}}, "description": "Plain text summary report"},
        404: {"description": "Summary not found or not owned by the caller"},
    },
)
def download_summary(
    summary_id: str,
    current_user: CurrentUser,
    db: DbSession,
) -> PlainTextResponse:
    started = time.perf_counter()
    service = SummarizationService(db)
    summary = service.get_owned_summary(current_user, summary_id)
    body = service.build_download_text(summary)

    MetricRepository(db).record(
        user_id=current_user.id,
        metric_type=MetricType.SUMMARY_DOWNLOAD,
        duration_seconds=round(time.perf_counter() - started, 4),
        attributes={"summary_id": str(summary.id)},
    )
    db.commit()

    filename = f"summary_{sanitize_filename(summary.request.title) or 'export'}.txt"
    return PlainTextResponse(
        content=body,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
