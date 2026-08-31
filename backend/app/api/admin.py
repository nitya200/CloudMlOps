"""Administrator endpoints (UC-14 Manage users, UC-15 Monitor usage/quality)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentAdmin, DbSession, Pagination
from app.models import UserRole
from app.schemas.admin import (
    PlatformStatsResponse,
    QualityMetricsResponse,
    UsageMetricsResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)
from app.schemas.auth import UserResponse
from app.schemas.common import Page
from app.services.admin_service import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    responses={403: {"description": "Administrator privileges required"}},
)


@router.get(
    "/users",
    response_model=Page[UserResponse],
    summary="List platform users",
)
def list_users(
    current_admin: CurrentAdmin,
    db: DbSession,
    pagination: Pagination,
    search: Annotated[str | None, Query(max_length=120, description="Name or email")] = None,
    role: Annotated[UserRole | None, Query(description="Filter by role")] = None,
) -> Page[UserResponse]:
    users, total = AdminService(db).list_users(
        search=search, role=role, limit=pagination.limit, offset=pagination.offset
    )
    return Page.build(
        [UserResponse.model_validate(user) for user in users],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.patch(
    "/users/{user_id}/status",
    response_model=UserResponse,
    summary="Activate or deactivate a user",
    responses={
        404: {"description": "User not found"},
        409: {"description": "Administrators cannot deactivate themselves"},
    },
)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_admin: CurrentAdmin,
    db: DbSession,
) -> UserResponse:
    """Deactivating a user also revokes their live sessions immediately."""
    user = AdminService(db).set_active(current_admin, user_id, payload.is_active)
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Change a user's role",
    responses={
        404: {"description": "User not found"},
        409: {"description": "Administrators cannot demote themselves"},
    },
)
def update_user_role(
    user_id: str,
    payload: UserRoleUpdate,
    current_admin: CurrentAdmin,
    db: DbSession,
) -> UserResponse:
    user = AdminService(db).set_role(current_admin, user_id, payload.role)
    return UserResponse.model_validate(user)


@router.get(
    "/stats",
    response_model=PlatformStatsResponse,
    summary="Platform-wide totals for the admin dashboard",
)
def platform_stats(current_admin: CurrentAdmin, db: DbSession) -> PlatformStatsResponse:
    return AdminService(db).platform_stats()


@router.get(
    "/usage",
    response_model=UsageMetricsResponse,
    summary="Usage telemetry grouped by request type and day",
)
def usage_metrics(
    current_admin: CurrentAdmin,
    db: DbSession,
    days: Annotated[int, Query(ge=1, le=90, description="Look-back window in days")] = 14,
) -> UsageMetricsResponse:
    return AdminService(db).usage_metrics(days=days)


@router.get(
    "/metrics",
    response_model=QualityMetricsResponse,
    summary="Summary quality metrics (ratings and success rate)",
)
def quality_metrics(current_admin: CurrentAdmin, db: DbSession) -> QualityMetricsResponse:
    return AdminService(db).quality_metrics()
