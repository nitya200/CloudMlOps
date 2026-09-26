"""Email verification + per-request summary style (proposal UC-1 / UC-5).

Revision ID: 0003_proposal_gaps
Revises: 0002_model_lifecycle
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.models.base import GUID, enum_column
from app.models.enums import SummaryStyle

revision: str = "0003_proposal_gaps"
down_revision: str | None = "0002_model_lifecycle"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "email_verification_tokens",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_email_verification_tokens_user_id", "email_verification_tokens", ["user_id"]
    )
    op.add_column(
        "summary_requests",
        sa.Column(
            "summary_style",
            enum_column(SummaryStyle, name="summary_style", length=20),
            nullable=False,
            server_default=SummaryStyle.CONCISE.value,
        ),
    )


def downgrade() -> None:
    op.drop_column("summary_requests", "summary_style")
    op.drop_index("ix_email_verification_tokens_user_id", table_name="email_verification_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_column("users", "email_verified")
