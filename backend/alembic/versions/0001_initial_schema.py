"""Initial schema: the seven core tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-31

Mirrors ``database/schema.sql``. The enum columns are built with the same
``enum_column`` helper the models use, so the CHECK constraints list lowercase
values ('user', 'admin') rather than member names ('USER', 'ADMIN').
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID, enum_column
from app.models.enums import (
    FileType,
    MetricType,
    RequestStatus,
    SourceType,
    SummaryLength,
    UserRole,
)

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", enum_column(UserRole, name="user_role", length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        _timestamp(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # The JWT "jti" claim, never the token itself.
        sa.Column("token_id", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        _timestamp(),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_index("ix_sessions_token_id", "sessions", ["token_id"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column(
            "file_type",
            enum_column(FileType, name="file_type", length=10),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(512), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("extracted_text", sa.Text(), nullable=False, server_default=""),
        _timestamp(),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "summary_requests",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            GUID(),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_type",
            enum_column(SourceType, name="source_type", length=20),
            nullable=False,
        ),
        sa.Column(
            "summary_length",
            enum_column(SummaryLength, name="summary_length", length=20),
            nullable=False,
            server_default=SummaryLength.MEDIUM.value,
        ),
        sa.Column("title", sa.String(255), nullable=False, server_default="Untitled"),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("input_word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            enum_column(RequestStatus, name="request_status", length=20),
            nullable=False,
            server_default=RequestStatus.PENDING.value,
        ),
        sa.Column("error_message", sa.String(500), nullable=True),
        _timestamp(),
    )
    op.create_index("ix_summary_requests_user_id", "summary_requests", ["user_id"])
    op.create_index("ix_summary_requests_document_id", "summary_requests", ["document_id"])

    op.create_table(
        "summaries",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "request_id",
            GUID(),
            sa.ForeignKey("summary_requests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("compression_ratio", sa.Float(), nullable=False, server_default="0"),
        sa.Column("processing_time_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("model_name", sa.String(120), nullable=False, server_default="unknown"),
        sa.Column("backend", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="1"),
        _timestamp(),
    )
    op.create_index("ix_summaries_request_id", "summaries", ["request_id"], unique=True)

    op.create_table(
        "feedback_records",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "summary_id",
            GUID(),
            sa.ForeignKey("summaries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.String(1000), nullable=True),
        _timestamp(),
        sa.CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
        sa.UniqueConstraint("summary_id", "user_id", name="uq_feedback_summary_user"),
    )
    op.create_index("ix_feedback_records_summary_id", "feedback_records", ["summary_id"])
    op.create_index("ix_feedback_records_user_id", "feedback_records", ["user_id"])

    op.create_table(
        "usage_metrics",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "user_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "metric_type",
            enum_column(MetricType, name="metric_type", length=40),
            nullable=False,
        ),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0"),
        sa.Column("detail", sa.String(500), nullable=True),
        sa.Column("attributes", sa.JSON(), nullable=True),
        _timestamp(),
    )
    op.create_index("ix_usage_metrics_user_id", "usage_metrics", ["user_id"])
    op.create_index("ix_usage_metrics_metric_type", "usage_metrics", ["metric_type"])


def downgrade() -> None:
    # Reverse dependency order so foreign keys never block a drop.
    for table in (
        "usage_metrics",
        "feedback_records",
        "summaries",
        "summary_requests",
        "documents",
        "sessions",
        "users",
    ):
        op.drop_table(table)
