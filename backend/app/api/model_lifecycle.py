"""Admin model registry and retraining endpoints (UC-12 / UC-16)."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentAdmin, DbSession
from app.core.exceptions import NotFoundError
from app.schemas.model_lifecycle import (
    ModelVersionResponse,
    TrainingJobCreate,
    TrainingJobResponse,
)
from app.services.model_lifecycle_service import ModelLifecycleService

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    responses={403: {"description": "Administrator privileges required"}},
)


@router.get(
    "/model-versions",
    response_model=list[ModelVersionResponse],
    summary="List registered model versions and ROUGE metrics",
)
def list_model_versions(current_admin: CurrentAdmin, db: DbSession) -> list[ModelVersionResponse]:
    return [
        ModelVersionResponse.model_validate(item)
        for item in ModelLifecycleService(db).list_versions()
    ]


@router.get(
    "/model-versions/active",
    response_model=ModelVersionResponse,
    summary="Return the model version currently promoted to production",
    responses={404: {"description": "No active model version"}},
)
def active_model_version(current_admin: CurrentAdmin, db: DbSession) -> ModelVersionResponse:
    version = ModelLifecycleService(db).get_active_version()
    if version is None:
        raise NotFoundError("No active model version is registered.")
    return ModelVersionResponse.model_validate(version)


@router.post(
    "/model-versions/{version_id}/approve",
    response_model=ModelVersionResponse,
    summary="Approve a evaluated model version (UC-12)",
)
def approve_model_version(
    version_id: str,
    current_admin: CurrentAdmin,
    db: DbSession,
) -> ModelVersionResponse:
    version = ModelLifecycleService(db).approve_version(current_admin, version_id)
    return ModelVersionResponse.model_validate(version)


@router.post(
    "/model-versions/{version_id}/promote",
    response_model=ModelVersionResponse,
    summary="Promote an approved version to active production (UC-12)",
)
def promote_model_version(
    version_id: str,
    current_admin: CurrentAdmin,
    db: DbSession,
) -> ModelVersionResponse:
    version = ModelLifecycleService(db).promote_version(current_admin, version_id)
    return ModelVersionResponse.model_validate(version)


@router.get(
    "/training-jobs",
    response_model=list[TrainingJobResponse],
    summary="List recent model retraining / evaluation jobs",
)
def list_training_jobs(current_admin: CurrentAdmin, db: DbSession) -> list[TrainingJobResponse]:
    return [
        TrainingJobResponse.model_validate(item) for item in ModelLifecycleService(db).list_jobs()
    ]


@router.post(
    "/training-jobs",
    response_model=TrainingJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger re-evaluation and register a new model version (UC-16)",
)
def trigger_training_job(
    payload: TrainingJobCreate,
    current_admin: CurrentAdmin,
    db: DbSession,
) -> TrainingJobResponse:
    job = ModelLifecycleService(db).trigger_retraining(current_admin, notes=payload.notes)
    return TrainingJobResponse.model_validate(job)
