"""Data tier wiring: engine, session factory and the FastAPI DB dependency."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Create an engine, adapting the pool to the target database.

    SQLite is only used by the test suite; it needs a shared in-memory pool and
    the ``check_same_thread`` escape hatch because TestClient uses threads.
    """
    kwargs: dict[str, Any] = {"echo": echo, "future": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if ":memory:" in database_url:
            kwargs["poolclass"] = StaticPool
    else:
        kwargs.update(
            pool_pre_ping=True,  # survives RDS idle-connection recycling
            pool_size=5,
            max_overflow=10,
            pool_recycle=1800,
        )
    return create_engine(database_url, **kwargs)


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
