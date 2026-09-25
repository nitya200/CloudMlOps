"""Model registry and retraining pipeline (UC-12 / UC-16)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import ModelVersionStatus, TrainingJobStatus
from app.services.model_lifecycle_service import ModelLifecycleService


class TestModelLifecycleAccess:
    def test_users_cannot_trigger_training(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.post("/api/admin/training-jobs", json={}, headers=user_headers)
        assert response.status_code == 403


class TestModelLifecycleFlow:
    def test_baseline_then_retrain_approve_promote(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        baseline = ModelLifecycleService(db).ensure_baseline()
        assert baseline is not None
        assert baseline.status == ModelVersionStatus.ACTIVE

        job_response = client.post(
            "/api/admin/training-jobs",
            json={"notes": "Quarterly evaluation"},
            headers=admin_headers,
        )
        assert job_response.status_code == 201, job_response.text
        job = job_response.json()
        assert job["status"] == TrainingJobStatus.COMPLETED.value
        assert job["model_version_id"]

        versions = client.get("/api/admin/model-versions", headers=admin_headers).json()
        assert len(versions) == 2
        candidate = next(v for v in versions if v["id"] == job["model_version_id"])
        assert candidate["status"] == ModelVersionStatus.PENDING_APPROVAL.value
        assert candidate["rouge_l"] is not None

        approved = client.post(
            f"/api/admin/model-versions/{candidate['id']}/approve",
            headers=admin_headers,
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == ModelVersionStatus.APPROVED.value

        promoted = client.post(
            f"/api/admin/model-versions/{candidate['id']}/promote",
            headers=admin_headers,
        )
        assert promoted.status_code == 200
        assert promoted.json()["status"] == ModelVersionStatus.ACTIVE.value

        active = client.get("/api/admin/model-versions/active", headers=admin_headers).json()
        assert active["id"] == candidate["id"]

        jobs = client.get("/api/admin/training-jobs", headers=admin_headers).json()
        assert jobs[0]["id"] == job["id"]
