"""Authentication endpoints (UC-01 Register, UC-02 Login, UC-03 Logout)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import CurrentUser, DbSession, client_ip, get_bearer_token, rate_limit
from app.core.config import settings
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import MessageResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Credential endpoints are the only ones an unauthenticated caller can reach in
# a loop, so they are the only ones that need a throttle.
login_throttle = rate_limit("login", settings.login_rate_limit, settings.login_rate_window_seconds)
register_throttle = rate_limit(
    "register", settings.register_rate_limit, settings.register_rate_window_seconds
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
    responses={
        409: {"description": "Email already registered"},
        429: {"description": "Too many registration attempts"},
    },
    dependencies=[Depends(register_throttle)],
)
def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    """Create a standard (non-admin) user account.

    Passwords are hashed with bcrypt; the plaintext is never stored or logged.
    """
    user, verification_required, message = AuthService(db).register(payload)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        verification_required=verification_required,
        message=message,
    )


@router.get(
    "/verify-email",
    response_model=UserResponse,
    summary="Confirm email ownership (proposal UC-1)",
)
def verify_email(db: DbSession, token: str = Query(..., min_length=16)) -> UserResponse:
    user = AuthService(db).verify_email(token)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for a JWT access token",
    responses={
        401: {"description": "Incorrect email or password"},
        403: {"description": "Account deactivated"},
        429: {"description": "Too many login attempts"},
    },
    dependencies=[Depends(login_throttle)],
)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    """Issue a bearer token and record a revocable server-side session."""
    token, expires_at, user = AuthService(db).login(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=client_ip(request),
    )
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current access token",
)
def logout(
    db: DbSession,
    token: Annotated[str, Depends(get_bearer_token)],
) -> MessageResponse:
    """Revoke the session server side so a stolen token stops working."""
    AuthService(db).logout(token)
    return MessageResponse(message="Signed out successfully.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated user's profile",
    responses={401: {"description": "Missing or invalid token"}},
)
def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
