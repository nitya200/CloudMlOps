"""Liveness/readiness endpoints.

AWS App Runner polls ``/health`` to decide whether to route traffic to an
instance, so it must stay dependency-light and always answer quickly.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app import __version__
from app.ai.factory import get_summarizer, resolve_backend
from app.api.deps import DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.common import HealthResponse

logger = get_logger(__name__)

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Service health check")
def health(db: DbSession) -> HealthResponse:
    database = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database = "unavailable"
        logger.error("database health check failed", extra={"error": str(exc)})

    try:
        summarizer = get_summarizer()
        backend, model, loaded = summarizer.backend, summarizer.model_name, summarizer.is_ready
    except Exception:
        backend, model, loaded = resolve_backend(), settings.ai_model_name, False

    return HealthResponse(
        status="ok" if database == "connected" else "degraded",
        environment=settings.environment,
        version=__version__,
        database=database,
        ai_backend=backend,
        ai_model=model,
        model_loaded=loaded,
    )


@router.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
