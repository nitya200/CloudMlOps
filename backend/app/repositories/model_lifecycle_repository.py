"""Persistence for model versions and training jobs."""

from __future__ import annotations

from sqlalchemy import func, select

from app.models import ModelVersion, ModelVersionStatus, TrainingJob
from app.repositories.base import BaseRepository


class ModelVersionRepository(BaseRepository[ModelVersion]):
    model = ModelVersion

    def get_active(self) -> ModelVersion | None:
        stmt = select(ModelVersion).where(ModelVersion.status == ModelVersionStatus.ACTIVE)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[ModelVersion]:
        stmt = select(ModelVersion).order_by(ModelVersion.created_at.desc())
        return list(self.db.execute(stmt).scalars())

    def get_by_label(self, version_label: str) -> ModelVersion | None:
        stmt = select(ModelVersion).where(ModelVersion.version_label == version_label)
        return self.db.execute(stmt).scalar_one_or_none()

    def next_version_label(self) -> str:
        stmt = select(func.count()).select_from(ModelVersion)
        count = int(self.db.execute(stmt).scalar() or 0)
        return f"v1.{count + 1}.0"

    def retire_active(self) -> None:
        active = self.get_active()
        if active is not None:
            active.status = ModelVersionStatus.RETIRED


class TrainingJobRepository(BaseRepository[TrainingJob]):
    model = TrainingJob

    def list_recent(self, *, limit: int = 20) -> list[TrainingJob]:
        stmt = select(TrainingJob).order_by(TrainingJob.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars())
