"""FastAPI application factory and entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.ai.factory import get_summarizer
from app.api import api_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.database import SessionLocal, create_schema
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.schemas.common import ErrorResponse
from app.services.auth_service import AuthService

configure_logging(settings.log_level, settings.log_json)
logger = get_logger("app.main")

DESCRIPTION = """
**CloudMLOps** is a three-tier AI document summarization platform.

* **Presentation tier** - React single page application
* **Business tier** - this FastAPI service (authentication, extraction, summarization)
* **Data tier** - PostgreSQL

Upload a PDF, DOCX or TXT file (or paste raw text) and the FLAN-T5 model
produces an abstractive summary. Every summary is stored so it can be
searched, re-read, downloaded and rated.

### Authentication
Call `POST /api/auth/login`, then send the returned token as
`Authorization: Bearer <token>` on every other request.
"""

TAGS_METADATA = [
    {"name": "System", "description": "Health and readiness probes."},
    {"name": "Authentication", "description": "Registration, login, logout and profile."},
    {"name": "Documents", "description": "Upload documents and extract their text."},
    {"name": "Summarization", "description": "Generate, read and download AI summaries."},
    {"name": "History", "description": "Browse, search and delete past summaries."},
    {"name": "Feedback", "description": "Rate the quality of a generated summary."},
    {"name": "Administration", "description": "User management and platform metrics."},
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown: schema, admin seed and model warm-up."""
    logger.info("starting %s v%s (%s)", settings.app_name, __version__, settings.environment)

    # Unlike a failed database connection, an insecure secret cannot be
    # reported through /health and left running: anyone who knows the default
    # can mint an admin token. Refuse to serve instead.
    if settings.is_production:
        problems = settings.insecure_production_settings()
        if problems:
            for problem in problems:
                logger.critical("insecure production configuration: %s", problem)
            raise RuntimeError(
                "Refusing to start in production with insecure configuration: " + " ".join(problems)
            )

    if settings.auto_create_schema:
        if settings.is_production:
            # create_all adds missing tables but never alters existing ones, so
            # the second schema change would silently not apply.
            logger.warning(
                "AUTO_CREATE_SCHEMA is enabled in production; "
                "prefer 'alembic upgrade head' so schema changes are versioned"
            )
        try:
            create_schema()
        except Exception as exc:
            # Do not crash the container: /health will report the failure and
            # App Runner can surface it instead of crash-looping.
            logger.error("could not create database schema", extra={"error": str(exc)})

    try:
        with SessionLocal() as db:
            AuthService(db).ensure_admin_account()
    except Exception as exc:
        logger.error("could not seed administrator", extra={"error": str(exc)})

    settings.storage_path.mkdir(parents=True, exist_ok=True)

    if settings.ai_eager_load:
        # Warming up here means the first user request is not the one that pays
        # the multi-second model load.
        try:
            summarizer = get_summarizer()
            summarizer.warmup()
            logger.info(
                "ai backend ready",
                extra={"backend": summarizer.backend, "model": summarizer.model_name},
            )
        except Exception as exc:
            logger.warning("ai warm-up skipped", extra={"error": str(exc)})

    yield
    logger.info("shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=DESCRIPTION,
        version=__version__,
        openapi_tags=TAGS_METADATA,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={"name": "CloudMLOps", "url": "https://github.com/"},
        license_info={"name": "MIT"},
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Request-ID", "X-Process-Time"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        """Attach a correlation id and duration to every request/response."""
        incoming = request.headers.get("x-request-id")
        request_id = incoming or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        elapsed = time.perf_counter() - started
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{elapsed:.4f}"
        if request.url.path not in ("/health", "/"):
            logger.info(
                "%s %s -> %s",
                request.method,
                request.url.path,
                response.status_code,
                extra={"duration_seconds": round(elapsed, 4)},
            )
        return response

    def error_response(status_code: int, code: str, message: str, details: dict) -> JSONResponse:
        payload = ErrorResponse(
            code=code, message=message, details=details, request_id=request_id_ctx.get()
        )
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Map domain errors to HTTP without leaking stack traces."""
        if exc.status_code >= 500:
            # 'message' is a reserved LogRecord attribute, hence the prefix.
            logger.error("domain error", extra={"code": exc.code, "error_message": exc.message})
        response = error_response(exc.status_code, exc.code, exc.message, exc.details)
        retry_after = getattr(exc, "retry_after", None)
        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
        return response

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        message = first.get("msg", "Request validation failed.")
        return error_response(
            422,
            "validation_error",
            f"{field}: {message}" if field else message,
            {"errors": [{k: str(v) for k, v in err.items()} for err in exc.errors()]},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return error_response(exc.status_code, "http_error", str(exc.detail), {})

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled exception", extra={"path": request.url.path})
        return error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred. Please try again.",
            {},
        )

    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
