"""Administrator API tests (UC-14, UC-15)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from tests.conftest import LONG_TEXT, auth_header, create_user, login


class TestAccessControl:
    def test_regular_users_are_rejected(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        for path in (
            "/api/admin/users",
            "/api/admin/stats",
            "/api/admin/usage",
            "/api/admin/metrics",
        ):
            response = client.get(path, headers=user_headers)
            assert response.status_code == 403, path
            assert response.json()["code"] == "permission_denied"

    def test_anonymous_callers_are_rejected(self, client: TestClient) -> None:
        assert client.get("/api/admin/users").status_code == 401

    def test_admins_are_allowed(self, client: TestClient, admin_headers: dict[str, str]) -> None:
        assert client.get("/api/admin/users", headers=admin_headers).status_code == 200


class TestUserManagement:
    def test_lists_users(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        create_user(db, email="a@example.com")
        create_user(db, email="b@example.com")

        response = client.get("/api/admin/users", headers=admin_headers).json()

        assert response["total"] == 3  # two users plus the admin

    def test_searches_by_email(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        target = create_user(db, email="findme@example.com", name="Findable Person")

        response = client.get("/api/admin/users?search=findme", headers=admin_headers).json()

        assert response["total"] == 1
        assert response["items"][0]["email"] == target.email

    def test_filters_by_role(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        create_user(db, email="plain@example.com")

        response = client.get("/api/admin/users?role=admin", headers=admin_headers).json()

        assert response["total"] == 1
        assert response["items"][0]["role"] == "admin"

    def test_deactivating_a_user_revokes_their_live_session(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        victim = create_user(db, email="victim@example.com", password="Password123")
        victim_headers = auth_header(login(client, victim.email, "Password123"))
        assert client.get("/api/auth/me", headers=victim_headers).status_code == 200

        response = client.patch(
            f"/api/admin/users/{victim.id}/status",
            json={"is_active": False},
            headers=admin_headers,
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False
        # The already-issued token must stop working immediately.
        assert client.get("/api/auth/me", headers=victim_headers).status_code == 401
        assert (
            client.post(
                "/api/auth/login",
                json={"email": victim.email, "password": "Password123"},
            ).status_code
            == 403
        )

    def test_reactivating_a_user_restores_login(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        victim = create_user(
            db, email="victim@example.com", password="Password123", is_active=False
        )

        client.patch(
            f"/api/admin/users/{victim.id}/status",
            json={"is_active": True},
            headers=admin_headers,
        )

        response = client.post(
            "/api/auth/login", json={"email": victim.email, "password": "Password123"}
        )
        assert response.status_code == 200

    def test_admin_cannot_deactivate_themselves(
        self, client: TestClient, admin: User, admin_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            f"/api/admin/users/{admin.id}/status",
            json={"is_active": False},
            headers=admin_headers,
        )

        assert response.status_code == 409

    def test_promotes_a_user_to_admin(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        target = create_user(db, email="promote@example.com")

        response = client.patch(
            f"/api/admin/users/{target.id}/role", json={"role": "admin"}, headers=admin_headers
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    def test_admin_cannot_demote_themselves(
        self, client: TestClient, admin: User, admin_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            f"/api/admin/users/{admin.id}/role", json={"role": "user"}, headers=admin_headers
        )

        assert response.status_code == 409

    def test_returns_404_for_an_unknown_user(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        response = client.patch(
            "/api/admin/users/00000000-0000-0000-0000-000000000000/status",
            json={"is_active": False},
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestReporting:
    def test_platform_stats_reflect_activity(
        self, client: TestClient, db: Session, admin_headers: dict[str, str]
    ) -> None:
        member = create_user(db, email="member@example.com", password="Password123")
        member_headers = auth_header(login(client, member.email, "Password123"))
        summary_id = client.post(
            "/api/summaries/text",
            json={"text": LONG_TEXT, "summary_length": "short"},
            headers=member_headers,
        ).json()["id"]
        client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 5}, headers=member_headers
        )

        stats = client.get("/api/admin/stats", headers=admin_headers).json()

        assert stats["total_users"] == 2
        assert stats["total_summaries"] == 1
        assert stats["total_requests"] == 1
        assert stats["total_feedback"] == 1
        assert stats["average_rating"] == 5.0
        assert stats["total_words_summarized"] > 0

    def test_usage_metrics_group_by_type(
        self, client: TestClient, admin_headers: dict[str, str], user_headers: dict[str, str]
    ) -> None:
        client.post(
            "/api/summaries/text",
            json={"text": LONG_TEXT, "summary_length": "short"},
            headers=user_headers,
        )

        usage = client.get("/api/admin/usage", headers=admin_headers).json()

        assert usage["counts_by_type"]["text_summarization"] == 1
        assert usage["counts_by_type"]["login"] >= 1
        assert isinstance(usage["daily_activity"], list)

    def test_quality_metrics_report_the_distribution(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        user_headers: dict[str, str],
        summary_id: str,
    ) -> None:
        client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 4}, headers=user_headers
        )

        metrics = client.get("/api/admin/metrics", headers=admin_headers).json()

        assert metrics["average_rating"] == 4.0
        assert metrics["rating_distribution"]["4"] == 1
        assert metrics["success_rate"] == 100.0

    def test_metrics_are_safe_on_an_empty_platform(
        self, client: TestClient, admin_headers: dict[str, str]
    ) -> None:
        stats = client.get("/api/admin/stats", headers=admin_headers).json()
        metrics = client.get("/api/admin/metrics", headers=admin_headers).json()

        # No division-by-zero when nothing has happened yet.
        assert stats["average_rating"] == 0
        assert stats["average_processing_time_seconds"] == 0
        assert metrics["success_rate"] == 0
