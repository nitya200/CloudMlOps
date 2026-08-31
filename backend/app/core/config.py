"""Central application configuration.

All tunables come from environment variables (12-factor style) so the exact
same container image runs locally, in CI, and on AWS App Runner.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

AIBackend = Literal["auto", "flan-t5", "extractive"]
StorageBackend = Literal["local", "s3"]

INSECURE_JWT_SECRET = "insecure-development-secret-change-me"
INSECURE_ADMIN_PASSWORD = "Admin123!"
MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Typed view over the process environment."""

    model_config = SettingsConfigDict(
        # Look for .env next to the backend first, then at the repo root, so a
        # single root .env works for both `uvicorn` from / and from /backend.
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    app_name: str = "CloudMLOps Document Summarizer"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api"
    log_level: str = "INFO"
    log_json: bool = False

    # ---- Data tier ----
    database_url: str = "postgresql+psycopg://cloudmlops:cloudmlops@localhost:5432/cloudmlops"
    db_echo: bool = False
    # create_all on startup keeps the student setup one-command simple; a real
    # production system would run Alembic migrations instead.
    auto_create_schema: bool = True

    # ---- Security ----
    jwt_secret_key: str = INSECURE_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    # 12 rounds is the production default; the test suite lowers this so that
    # hashing does not dominate the runtime.
    bcrypt_rounds: int = 12

    # ---- CORS ----
    # Stored as a plain string so pydantic-settings does not attempt JSON decoding
    # on a list field (which rejects comma-separated values from .env files).
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
    )

    # ---- Rate limiting ----
    # Counted per client IP, never per email: keying on the account would let an
    # attacker lock a victim out of their own login.
    rate_limit_enabled: bool = True
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 300
    register_rate_limit: int = 5
    register_rate_window_seconds: int = 3600

    # ---- Uploads ----
    storage_backend: StorageBackend = "local"
    storage_dir: Path = Path("storage/uploads")
    max_upload_size_mb: int = 10
    s3_bucket: str | None = None
    s3_prefix: str = "documents"
    s3_region: str | None = None

    # ---- AI ----
    ai_backend: AIBackend = "auto"
    ai_model_name: str = "google/flan-t5-small"
    ai_model_cache_dir: Path | None = None
    ai_max_input_chars: int = 60_000
    ai_chunk_tokens: int = 420
    # Skip loading the real model during tests so the suite stays fast.
    ai_eager_load: bool = True

    # ---- Bootstrap admin ----
    seed_admin: bool = True
    # A real TLD is required: the login schema validates with EmailStr, and
    # email-validator rejects reserved names such as ".local".
    admin_email: str = "admin@cloudmlops.app"
    admin_password: str = INSECURE_ADMIN_PASSWORD
    admin_name: str = "Platform Administrator"

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS from either comma-separated or JSON list form."""
        stripped = self.cors_origins.strip()
        if stripped.startswith("["):
            parsed = json.loads(stripped)
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def storage_path(self) -> Path:
        path = self.storage_dir
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def insecure_production_settings(self) -> list[str]:
        """List the settings that must never ship to production as defaults.

        Returned rather than raised so the check is a pure function the tests
        can exercise without constructing a whole environment.
        """
        problems: list[str] = []
        if self.jwt_secret_key == INSECURE_JWT_SECRET:
            problems.append("JWT_SECRET_KEY is still the built-in development value.")
        elif len(self.jwt_secret_key) < MIN_PRODUCTION_SECRET_LENGTH:
            problems.append(
                f"JWT_SECRET_KEY must be at least {MIN_PRODUCTION_SECRET_LENGTH} characters."
            )
        if self.seed_admin and self.admin_password == INSECURE_ADMIN_PASSWORD:
            problems.append("ADMIN_PASSWORD is still the built-in default.")
        if self.storage_backend == "s3" and not self.s3_bucket:
            problems.append("STORAGE_BACKEND is 's3' but S3_BUCKET is not set.")
        if any(origin == "*" for origin in self.cors_origin_list):
            problems.append("CORS_ORIGINS must name explicit origins, not '*'.")
        return problems


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the environment is parsed once per process."""
    return Settings()


settings = get_settings()
