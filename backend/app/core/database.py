"""Data tier wiring: engine, session factory and the FastAPI DB dependency."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _parse_postgres_url(database_url: str) -> tuple[str, int, str]:
    """Extract host, port and username from a PostgreSQL SQLAlchemy URL."""
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    if not parsed.hostname or not parsed.username:
        raise ValueError("DATABASE_URL must include a hostname and username for IAM auth.")
    port = parsed.port or 5432
    return parsed.hostname, port, parsed.username


def _should_use_iam_auth(database_url: str) -> bool:
    """True when IAM tokens are required (explicit flag or passwordless RDS URL)."""
    if database_url.startswith("sqlite"):
        return False
    if settings.database_iam_auth:
        return True
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    return bool(parsed.username and not parsed.password and parsed.hostname)


def _postgres_dbname(database_url: str) -> str:
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    path = urlparse(normalized).path.lstrip("/")
    return path or "postgres"


def _generate_iam_auth_token(host: str, port: int, username: str) -> str:
    import boto3

    region = settings.s3_region or settings.aws_region
    return boto3.client("rds", region_name=region).generate_db_auth_token(
        DBHostname=host,
        Port=port,
        DBUsername=username,
        Region=region,
    )


def build_engine(
    database_url: str,
    *,
    echo: bool = False,
    poolclass: type | None = None,
) -> Engine:
    """Create an engine, adapting the pool to the target database.

    SQLite is only used by the test suite; it needs a shared in-memory pool and
    the ``check_same_thread`` escape hatch because TestClient uses threads.
    """
    kwargs: dict[str, Any] = {"echo": echo, "future": True}
    if poolclass is not None:
        kwargs["poolclass"] = poolclass
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    else:
        kwargs["pool_pre_ping"] = True
        if poolclass is None:
            kwargs.update(
                pool_size=5,
                max_overflow=10,
                pool_recycle=1800,
            )

    if _should_use_iam_auth(database_url):
        import psycopg

        host, port, username = _parse_postgres_url(database_url)
        dbname = _postgres_dbname(database_url)

        def _connect_with_iam_token() -> Any:
            token = _generate_iam_auth_token(host, port, username)
            return psycopg.connect(
                host=host,
                port=port,
                user=username,
                password=token,
                dbname=dbname,
                sslmode="require",
            )

        engine = create_engine("postgresql+psycopg://", creator=_connect_with_iam_token, **kwargs)
        logger.info("database IAM authentication enabled", extra={"host": host, "user": username})
        return engine

    engine = create_engine(database_url, **kwargs)
    return engine


engine: Engine = build_engine(settings.database_url, echo=settings.db_echo)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Request-scoped session. Commits are the service layer's responsibility."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_schema() -> None:
    """Create any missing tables. Idempotent."""
    from app.models import Base  # imported here so all models are registered

    Base.metadata.create_all(bind=engine)
    logger.info("database schema verified", extra={"tables": len(Base.metadata.tables)})
