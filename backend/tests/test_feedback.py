"""Summary rating tests (UC-13)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import FeedbackRecord
from tests.conftest import auth_header, create_user, login


class TestSubmitFeedback:
    def test_records_a_rating(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.post(
            "/api/feedback",
            json={"summary_id": summary_id, "rating": 5, "comment": "Very useful summary"},
            headers=user_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["rating"] == 5
        assert body["comment"] == "Very useful summary"

    def test_rating_appears_on_the_summary_detail(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 4}, headers=user_headers
        )

        detail = client.get(f"/api/summaries/{summary_id}", headers=user_headers).json()
        assert detail["my_rating"] == 4

    def test_re_rating_updates_instead_of_duplicating(
        self, client: TestClient, db: Session, user_headers: dict[str, str], summary_id: str
    ) -> None:
        client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 2}, headers=user_headers
        )
        response = client.post(
            "/api/feedback",
            json={"summary_id": summary_id, "rating": 5, "comment": "Changed my mind"},
            headers=user_headers,
        )

        assert response.status_code == 201
        assert db.query(FeedbackRecord).count() == 1
        assert db.query(FeedbackRecord).one().rating == 5

    def test_blank_comment_is_stored_as_null(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.post(
            "/api/feedback",
            json={"summary_id": summary_id, "rating": 3, "comment": "   "},
            headers=user_headers,
        )

        assert response.json()["comment"] is None

    def test_rejects_a_rating_above_five(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 6}, headers=user_headers
        )
        assert response.status_code == 422

    def test_rejects_a_rating_below_one(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 0}, headers=user_headers
        )
        assert response.status_code == 422

    def test_rejects_an_over_long_comment(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.post(
            "/api/feedback",
            json={"summary_id": summary_id, "rating": 3, "comment": "x" * 1001},
            headers=user_headers,
        )
        assert response.status_code == 422

    def test_cannot_rate_another_users_summary(
        self, client: TestClient, db: Session, summary_id: str
    ) -> None:
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))

        response = client.post(
            "/api/feedback", json={"summary_id": summary_id, "rating": 5}, headers=other_headers
        )

        assert response.status_code == 404

    def test_returns_404_for_an_unknown_summary(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/feedback",
            json={"summary_id": "00000000-0000-0000-0000-000000000000", "rating": 5},
            headers=user_headers,
        )
        assert response.status_code == 404

    def test_requires_authentication(self, client: TestClient, summary_id: str) -> None:
        response = client.post("/api/feedback", json={"summary_id": summary_id, "rating": 5})
        assert response.status_code == 401


class TestListFeedback:
    def test_lists_the_feedback_for_a_summary(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        client.post(
            "/api/feedback",
            json={"summary_id": summary_id, "rating": 4, "comment": "Good"},
            headers=user_headers,
        )

        response = client.get(f"/api/feedback/summary/{summary_id}", headers=user_headers)

        assert response.status_code == 200
        assert len(response.json()) == 1
