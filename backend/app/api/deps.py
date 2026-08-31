"""Shared FastAPI dependencies: DB session, current user, admin guard."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError, RateLimitError
from app.core.logging import get_logger
from app.core.rate_limit import limiter
from app.models import User
from app.services.auth_service import AuthService

logger = get_logger(__name__)

# auto_error=False so a missing header produces our own 401 payload shape
# instead of FastAPI's default, keeping the error contract consistent.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication required.")
    return AuthService(db).resolve_token(credentials.credentials)


def get_current_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if not user.is_admin:
        raise PermissionDeniedError("Administrator privileges are required for this operation.")
    return user


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
) -> str:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Authentication required.")
    return credentials.credentials


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """Page/size query parameters shared by all list endpoints."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination_params(
    page: int = Query(1, ge=1, description="1-based page number"),
    page_size: int = Query(10, ge=1, le=100, description="Rows per page"),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)


def client_ip(request: Request) -> str | None:
    """Best-effort client IP, honouring the App Runner / ALB proxy header."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def rate_limit(bucket: str, limit: int, window_seconds: int) -> Callable[[Request], None]:
    """Build a dependency that caps how often one client may hit an endpoint.

    Keyed on the client IP alone. Including the submitted email would let an
    attacker deliberately exhaust a victim's budget and lock them out.
    """

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        key = f"{bucket}:{client_ip(request) or 'unknown'}"
        retry_after = limiter.hit(key, limit=limit, window_seconds=window_seconds)
        if retry_after is None:
            return
        logger.warning("rate limit exceeded", extra={"bucket": bucket})
        raise RateLimitError(
            "Too many attempts. Please wait before trying again.",
            retry_after=int(retry_after) + 1,
        )

    return dependency


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]
Pagination = Annotated[PaginationParams, Depends(pagination_params)]
