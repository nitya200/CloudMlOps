"""Model registry, evaluation, and promotion (UC-12 / UC-16)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.ai.factory import get_summarizer, resolve_backend
from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.ml.evaluation_compare import evaluate_with_baseline, format_evaluation_notes
from app.ml.evaluation_corpus import EVALUATION_SAMPLES
from app.models import (
    ModelVersion,
    ModelVersionStatus,
    TrainingJob,
    TrainingJobStatus,
    User,
)
from app.repositories.model_lifecycle_repository import (
    ModelVersionRepository,
    TrainingJobRepository,
)

logger = get_logger(__name__)


class ModelLifecycleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.versions = ModelVersionRepository(db)
        self.jobs = TrainingJobRepository(db)

    def ensure_baseline(self) -> ModelVersion | None:
        """Register the running summarizer as v1.0.0 when the registry is empty."""
        if self.versions.count() > 0:
            return self.versions.get_active()
        summarizer = get_summarizer()
        version = ModelVersion(
            version_label="v1.0.0",
            base_model_name=summarizer.model_name,
            backend=summarizer.backend,
            status=ModelVersionStatus.ACTIVE,
            promoted_at=datetime.now(UTC),
            evaluation_notes="Baseline registered from runtime configuration.",
        )
        self.db.add(version)
        self.db.commit()
        logger.info("baseline model version registered", extra={"version": version.version_label})
        return version

    def list_versions(self) -> list[ModelVersion]:
        return self.versions.list_all()

    def get_active_version(self) -> ModelVersion | None:
        return self.versions.get_active()

    def list_jobs(self) -> list[TrainingJob]:
        return self.jobs.list_recent()

    def approve_version(self, admin: User, version_id: uuid.UUID | str) -> ModelVersion:
        version = self._get_version(version_id)
        if version.status != ModelVersionStatus.PENDING_APPROVAL:
            raise ConflictError(
                "Only versions awaiting approval can be approved. "
                f"Current status: {version.status.value}."
            )
        version.status = ModelVersionStatus.APPROVED
        version.approved_at = datetime.now(UTC)
        version.approved_by_id = admin.id
        self.db.commit()
        logger.info(
            "model version approved",
            extra={"version": version.version_label, "by": str(admin.id)},
        )
        return version

    def promote_version(self, admin: User, version_id: uuid.UUID | str) -> ModelVersion:
        version = self._get_version(version_id)
        if version.status not in (
            ModelVersionStatus.APPROVED,
            ModelVersionStatus.PENDING_APPROVAL,
            ModelVersionStatus.ACTIVE,
        ):
            raise ConflictError(
                "Only approved or pending versions can be promoted to production."
            )
        self.versions.retire_active()
        version.status = ModelVersionStatus.ACTIVE
        version.promoted_at = datetime.now(UTC)
        if version.approved_at is None:
            version.approved_at = datetime.now(UTC)
            version.approved_by_id = admin.id
        self.db.commit()
        logger.info(
            "model version promoted",
            extra={"version": version.version_label, "by": str(admin.id)},
        )
        return version

    def trigger_retraining(self, admin: User, *, notes: str | None = None) -> TrainingJob:
        """UC-16: queue evaluation of the current summarizer and register a new version."""
        self.ensure_baseline()
        job = TrainingJob(
            status=TrainingJobStatus.RUNNING,
            triggered_by_id=admin.id,
            progress_message="Evaluating summarizer on the holdout corpus…",
        )
        self.db.add(job)
        self.db.flush()

        label = self.versions.next_version_label()
        version = ModelVersion(
            version_label=label,
            base_model_name=settings.ai_model_name,
            backend=resolve_backend(),
            status=ModelVersionStatus.EVALUATING,
            evaluation_notes=notes,
        )
        self.db.add(version)
        self.db.flush()
        job.model_version_id = version.id

        try:
            comparison = evaluate_with_baseline(get_summarizer())
            candidate = comparison["candidate_rouge"]
            version.rouge_1 = candidate["rouge_1"]
            version.rouge_2 = candidate["rouge_2"]
            version.rouge_l = candidate["rouge_l"]
            version.evaluation_notes = format_evaluation_notes(comparison)
            version.status = ModelVersionStatus.PENDING_APPROVAL
            job.status = TrainingJobStatus.COMPLETED
            baseline_l = comparison["baseline_rouge"]["rouge_l"]
            job.progress_message = (
                f"ROUGE-L candidate={candidate['rouge_l']:.4f} vs baseline={baseline_l:.4f} "
                f"({len(EVALUATION_SAMPLES)} samples); awaiting admin approval."
            )
            job.finished_at = datetime.now(UTC)
        except Exception as exc:
            version.status = ModelVersionStatus.FAILED
            job.status = TrainingJobStatus.FAILED
            job.error_message = str(exc)[:480]
            job.progress_message = "Evaluation failed."
            job.finished_at = datetime.now(UTC)
            logger.exception("model evaluation failed")

        self.db.commit()
        self.db.refresh(job)
        return job

    def _get_version(self, version_id: uuid.UUID | str) -> ModelVersion:
        version = self.versions.get(version_id)
        if version is None:
            raise NotFoundError("Model version not found.")
        return version


__all__ = ["ModelLifecycleService"]
