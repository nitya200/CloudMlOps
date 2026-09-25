"""Authentication and identity business logic."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, PermissionDeniedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import EmailVerificationToken, MetricType, User, UserRole
from app.services.email_service import send_verification_email
from app.repositories import MetricRepository, SessionRepository, UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest

logger = get_logger(__name__)


class AuthService:
    """Owns registration, login, logout and token resolution."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.sessions = SessionRepository(db)
        self.metrics = MetricRepository(db)

    # ---- UC-01 Register ---------------------------------------------------
    def register(
        self, payload: RegisterRequest, *, role: UserRole = UserRole.USER
    ) -> tuple[User, bool, str | None]:
        email = payload.email.strip().lower()
        if self.users.email_exists(email):
            raise ConflictError("An account with this email address already exists.")

        must_verify = settings.require_email_verification and role == UserRole.USER
        user = self.users.create(
            name=payload.name,
            email=email,
            password_hash=hash_password(payload.password),
            role=role,
            is_active=True,
            email_verified=not must_verify,
        )
        message: str | None = None
        if must_verify:
            raw = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw.encode()).hexdigest()
            expires = datetime.now(UTC) + timedelta(hours=settings.email_verification_expire_hours)
            self.db.add(
                EmailVerificationToken(
                    user_id=user.id, token_hash=token_hash, expires_at=expires
                )
            )
            verify_url = f"{settings.public_app_url.rstrip('/')}/verify-email?token={raw}"
            send_verification_email(to_email=user.email, verify_url=verify_url)
            message = "Check your email for a verification link before signing in."
        self.metrics.record(
            user_id=user.id,
            metric_type=MetricType.REGISTRATION,
            detail=f"role={role}",
        )
        self.db.commit()
        logger.info("user registered", extra={"user_id": str(user.id), "role": str(role)})
        return user, must_verify, message

    def verify_email(self, raw_token: str) -> User:
        token_hash = hashlib.sha256(raw_token.strip().encode()).hexdigest()
        stmt = select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        record = self.db.execute(stmt).scalar_one_or_none()
        if record is None:
            raise AuthenticationError("Invalid or expired verification link.")
        if record.expires_at < datetime.now(UTC):
            raise AuthenticationError("Verification link has expired. Register again or request a new link.")
        user = self.users.get(record.user_id)
        if user is None:
            raise AuthenticationError("Account not found.")
        user.email_verified = True
        self.db.delete(record)
        self.db.commit()
        logger.info("email verified", extra={"user_id": str(user.id)})
        return user

    # ---- UC-02 Login -----------------------------------------------------
    def login(
        self,
        payload: LoginRequest,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> tuple[str, datetime, User]:
        user = self.users.get_by_email(payload.email)
        # Same message for "no such user" and "wrong password" so the endpoint
        # cannot be used to enumerate registered email addresses.
        invalid = AuthenticationError("Incorrect email or password.")
        if user is None or not verify_password(payload.password, user.password_hash):
            self.metrics.record(
                user_id=user.id if user else None,
                metric_type=MetricType.LOGIN,
                success=False,
                detail="invalid credentials",
            )
            self.db.commit()
            raise invalid
        if not user.is_active:
            raise PermissionDeniedError("This account has been deactivated by an administrator.")
        if settings.require_email_verification and not user.email_verified:
            raise PermissionDeniedError(
                "Verify your email address before signing in. Check your inbox for the link."
            )

        token, expires_at, token_id = create_access_token(user.id, role=str(user.role))
        self.sessions.create(
            user_id=user.id,
            token_id=token_id,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:255] or None,
            ip_address=(ip_address or "")[:64] or None,
        )
        self.metrics.record(user_id=user.id, metric_type=MetricType.LOGIN, success=True)
        self.db.commit()
        logger.info("login succeeded", extra={"user_id": str(user.id)})
        return token, expires_at, user

    # ---- UC-03 Logout ----------------------------------------------------
    def logout(self, token: str) -> bool:
        try:
            claims = decode_access_token(token)
        except AuthenticationError:
            return False  # already invalid; treat logout as idempotent
        revoked = self.sessions.revoke(str(claims.get("jti", "")))
        self.db.commit()
        return revoked

    # ---- Token resolution (used by the FastAPI dependency) ---------------
    def resolve_token(self, token: str) -> User:
        claims = decode_access_token(token)
        token_id = str(claims.get("jti", ""))
        subject = claims.get("sub")
        if not token_id or not subject:
            raise AuthenticationError("Malformed authentication token.")

        session = self.sessions.get_by_token_id(token_id)
        if session is None or not session.is_valid:
            raise AuthenticationError("Session is no longer valid, please sign in again.")

        user = self.users.get(subject)
        if user is None:
            raise AuthenticationError("Account no longer exists.")
        if not user.is_active:
            raise PermissionDeniedError("This account has been deactivated by an administrator.")
        return user

    # ---- Bootstrap -------------------------------------------------------
    def ensure_admin_account(self) -> User | None:
        """Create the configured administrator on first boot.

        Without this there would be no way to reach the admin endpoints on a
        fresh database.
        """
        if not settings.seed_admin:
            return None
        existing = self.users.get_by_email(settings.admin_email)
        if existing is not None:
            return existing
        user = self.users.create(
            name=settings.admin_name,
            email=settings.admin_email.strip().lower(),
            password_hash=hash_password(settings.admin_password),
            role=UserRole.ADMIN,
            is_active=True,
            email_verified=True,
        )
        self.db.commit()
        logger.warning(
            "seeded default administrator - change the password immediately",
            extra={"email": user.email},
        )
        return user
