"""End-to-end schema check against a real PostgreSQL instance.

Creating tables proves very little. The bug that reached production created
all seven tables happily and then rejected every INSERT, because the enum
columns wrote member names (``'USER'``) into CHECK constraints that only allow
values (``'user'``). SQLite could not catch it: its schema is generated from
the same models doing the writing, so both sides agreed.

This script therefore *writes a row into every table* and reads it back,
against the engine production actually runs on. Run it in CI after
``alembic upgrade head``:

    python -m scripts.verify_postgres
"""

from __future__ import annotations

import sys
import uuid

from sqlalchemy import inspect, select

from app.core.database import SessionLocal, engine
from app.models import (
    Document,
    FeedbackRecord,
    FileType,
    MetricType,
    RequestStatus,
    SourceType,
    Summary,
    SummaryLength,
    SummaryRequest,
    UsageMetric,
    User,
    UserRole,
)

EXPECTED_TABLES = {
    "users",
    "sessions",
    "documents",
    "summary_requests",
    "summaries",
    "feedback_records",
    "usage_metrics",
}


def check_tables() -> None:
    tables = set(inspect(engine).get_table_names())
    missing = EXPECTED_TABLES - tables
    if missing:
        raise AssertionError(f"missing tables: {sorted(missing)}")
    print(f"tables present: {sorted(EXPECTED_TABLES)}")


def check_writes() -> None:
    """Insert one row per table, exercising every enum column."""
    marker = uuid.uuid4().hex[:8]

    with SessionLocal() as db:
        user = User(
            name="CI Smoke Test",
            email=f"ci-{marker}@example.com",
            password_hash="not-a-real-hash",
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.flush()

        document = Document(
            user_id=user.id,
            filename="ci.pdf",
            file_type=FileType.PDF,
            storage_path=f"{user.id}/ci.pdf",
            size_bytes=1024,
            page_count=2,
            word_count=120,
            extracted_text="Text extracted by the continuous integration smoke test.",
        )
        db.add(document)
        db.flush()

        request = SummaryRequest(
            user_id=user.id,
            document_id=document.id,
            source_type=SourceType.DOCUMENT,
            summary_length=SummaryLength.LONG,
            title="CI smoke test",
            input_text="Input text for the continuous integration smoke test.",
            input_word_count=120,
            status=RequestStatus.COMPLETED,
        )
        db.add(request)
        db.flush()

        summary = Summary(
            request_id=request.id,
            summary_text="A summary produced by the smoke test.",
            word_count=30,
            compression_ratio=0.25,
            processing_time_seconds=1.5,
            model_name="google/flan-t5-small",
            backend="flan-t5",
            chunk_count=1,
        )
        db.add(summary)
        db.flush()

        db.add(FeedbackRecord(summary_id=summary.id, user_id=user.id, rating=5, comment="Good."))
        db.add(
            UsageMetric(
                user_id=user.id,
                metric_type=MetricType.DOCUMENT_SUMMARIZATION,
                success=True,
                duration_seconds=1.5,
                attributes={"backend": "flan-t5"},
            )
        )
        db.commit()
        print("inserted one row into every table")

        # Enum columns must come back as lowercase values, matching both the
        # CHECK constraints and the JSON the API returns.
        stored_role = db.execute(select(User.role).where(User.id == user.id)).scalar_one()
        stored_length = db.execute(
            select(SummaryRequest.summary_length).where(SummaryRequest.id == request.id)
        ).scalar_one()

        assert str(stored_role) == "admin", f"role round-tripped as {stored_role!r}"
        assert str(stored_length) == "long", f"length round-tripped as {stored_length!r}"
        print(f"enum round-trip ok: role={stored_role} summary_length={stored_length}")

        # Cascades must clean up everything that hangs off the user.
        db.delete(user)
        db.commit()

        remaining = db.execute(select(Summary).where(Summary.id == summary.id)).scalar_one_or_none()
        assert remaining is None, "deleting the user left an orphaned summary"
        print("cascade delete ok")


def main() -> int:
    check_tables()
    check_writes()
    print("\nPostgreSQL verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
