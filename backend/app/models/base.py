"""Declarative base, portable UUID column type and shared mixins."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import CHAR, DateTime, Enum, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Root of the ORM hierarchy."""


def enum_column(enum_cls: type[enum.Enum], *, name: str, length: int) -> Enum:
    """Store an enum by its ``value`` rather than its member name.

    Two settings here are load bearing, and both were learned the hard way:

    ``values_callable`` — SQLAlchemy persists member *names* by default, which
    writes ``'USER'`` where ``database/schema.sql`` and the JSON API both use
    ``'user'``.

    ``create_constraint`` — defaults to ``False`` in SQLAlchemy 2.0, so no
    CHECK constraint is emitted and any string is accepted. The hand-written
    DDL *does* constrain these columns, so leaving it off let SQLite accept
    values that PostgreSQL then rejected in production. Turning it on makes
    the test database enforce exactly what the real one does.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        validate_strings=True,
        create_constraint=True,
        values_callable=lambda cls: [member.value for member in cls],
    )


class GUID(TypeDecorator):
    """UUID column that is native on PostgreSQL and CHAR(36) elsewhere.

    Production runs on RDS PostgreSQL with a real ``uuid`` type; the test suite
    runs on SQLite. This decorator keeps a single set of models for both.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        return value if dialect.name == "postgresql" else str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))


def utcnow() -> datetime:
    return datetime.now(UTC)


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
