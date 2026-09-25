"""Model registry and training jobs (UC-12 / UC-16).

Revision ID: 0002_model_lifecycle
Revises: 0001_initial
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID, enum_column
from app.models.enums import ModelVersionStatus, TrainingJobStatus

revision: str = "0002_model_lifecycle"
down_revision: str | None = "0001_initial"
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
        "model_versions",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("version_label", sa.String(64), nullable=False, unique=True),
        sa.Column("base_model_name", sa.String(200), nullable=False),
        sa.Column("backend", sa.String(32), nullable=False),
        sa.Column(
            "status",
            enum_column(ModelVersionStatus, name="model_version_status", length=32),
            nullable=False,
        ),
        sa.Column("rouge_1", sa.Float(), nullable=True),
        sa.Column("rouge_2", sa.Float(), nullable=True),
        sa.Column("rouge_l", sa.Float(), nullable=True),
        sa.Column("evaluation_notes", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        _timestamp(),
    )

    op.create_table(
        "training_jobs",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column(
            "status",
            enum_column(TrainingJobStatus, name="training_job_status", length=20),
            nullable=False,
        ),
        sa.Column(
            "triggered_by_id",
            GUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            GUID(),
            sa.ForeignKey("model_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("progress_message", sa.String(500), nullable=False, server_default=""),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        _timestamp(),
    )
    op.create_index("ix_training_jobs_model_version_id", "training_jobs", ["model_version_id"])


def downgrade() -> None:
    op.drop_table("training_jobs")
    op.drop_table("model_versions")
