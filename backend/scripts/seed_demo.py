"""Populate the database with demo data for a walkthrough or screenshots.

Run from the ``backend`` directory:

    python -m scripts.seed_demo

Idempotent: existing rows are left alone, so it is safe to run repeatedly.
Credentials are hashed at run time with the application's own hashing function,
which is why this lives here instead of in database/seed.sql.
"""

from __future__ import annotations

import sys
import uuid

from app.core.database import SessionLocal, create_schema
from app.core.security import hash_password
from app.models import (
    FeedbackRecord,
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
from app.repositories import UserRepository

DEMO_PASSWORD = "Password123"

DEMO_USERS = [
    ("Demo Administrator", "demo.admin@cloudmlops.app", UserRole.ADMIN, True),
    ("Demo Analyst", "demo.analyst@cloudmlops.app", UserRole.USER, True),
    ("Suspended Account", "demo.suspended@cloudmlops.app", UserRole.USER, False),
]

SOURCE_TEXT = (
    "Cloud native machine learning platforms have changed how teams ship models. "
    "Containerized inference services can be deployed with the same pipeline as any "
    "other web application, which lowers the operational barrier considerably. "
    "This document evaluates whether a small instruction tuned model is sufficient "
    "for summarizing internal reports, and concludes that it is for the majority of "
    "day to day cases. The remaining gap is in documents that mix dense tables with "
    "narrative text, where extraction quality matters more than model size."
)

DEMO_SUMMARY = (
    "Containerizing inference lets machine learning teams reuse their existing "
    "deployment pipelines, and a small instruction tuned model is good enough to "
    "summarize most internal reports. Documents that mix tables with prose remain "
    "the weak point, and there the bottleneck is text extraction rather than the model."
)

# Fixed ids keep repeated runs idempotent.
REQUEST_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")
SUMMARY_ID = uuid.UUID("55555555-5555-4555-8555-555555555555")


def main() -> int:
    create_schema()
    with SessionLocal() as db:
        users = UserRepository(db)
        created: dict[str, User] = {}

        for name, email, role, is_active in DEMO_USERS:
            existing = users.get_by_email(email)
            if existing is None:
                existing = users.create(
                    name=name,
                    email=email,
                    password_hash=hash_password(DEMO_PASSWORD),
                    role=role,
                    is_active=is_active,
                )
                print(f"created user  {email} ({role})")
            else:
                print(f"user exists   {email}")
            created[email] = existing

        analyst = created["demo.analyst@cloudmlops.app"]

        if db.get(SummaryRequest, REQUEST_ID) is None:
            word_count = len(SOURCE_TEXT.split())
            summary_words = len(DEMO_SUMMARY.split())
            db.add(
                SummaryRequest(
                    id=REQUEST_ID,
                    user_id=analyst.id,
                    document_id=None,
                    source_type=SourceType.TEXT,
                    summary_length=SummaryLength.MEDIUM,
                    title="Cloud native machine learning platforms",
                    input_text=SOURCE_TEXT,
                    input_word_count=word_count,
                    status=RequestStatus.COMPLETED,
                )
            )
            db.add(
                Summary(
                    id=SUMMARY_ID,
                    request_id=REQUEST_ID,
                    summary_text=DEMO_SUMMARY,
                    word_count=summary_words,
                    compression_ratio=round(summary_words / word_count, 4),
                    processing_time_seconds=1.62,
                    model_name="google/flan-t5-small",
                    backend="flan-t5",
                    chunk_count=1,
                )
            )
            db.flush()
            db.add(
                FeedbackRecord(
                    summary_id=SUMMARY_ID,
                    user_id=analyst.id,
                    rating=4,
                    comment="Accurate, though it dropped the deployment detail I cared about.",
                )
            )
            for metric_type, duration in (
                (MetricType.LOGIN, 0.08),
                (MetricType.TEXT_SUMMARIZATION, 1.62),
                (MetricType.FEEDBACK, 0.02),
            ):
                db.add(
                    UsageMetric(
                        user_id=analyst.id,
                        metric_type=metric_type,
                        success=True,
                        duration_seconds=duration,
                    )
                )
            print("created demo summary, rating and usage metrics")
        else:
            print("demo summary exists")

        db.commit()

    print(f"\nDone. All demo accounts share the password: {DEMO_PASSWORD}")
    print("Change or remove them before exposing this deployment to anyone else.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
