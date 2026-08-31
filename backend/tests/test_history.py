"""Summary history tests (UC-10 view, UC-11 search, UC-12 delete)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Summary, SummaryRequest
from tests.conftest import LONG_TEXT, auth_header, create_user, login


def create_summary(client: TestClient, headers: dict[str, str], title: str) -> str:
    response = client.post(
        "/api/summaries/text",
        json={"text": LONG_TEXT, "summary_length": "short", "title": title},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


class TestListHistory:
    def test_returns_newest_first(self, client: TestClient, user_headers: dict[str, str]) -> None:
        for title in ("Oldest report", "Middle report", "Newest report"):
            create_summary(client, user_headers, title)

        response = client.get("/api/history", headers=user_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert body["items"][0]["title"] == "Newest report"

    def test_paginates(self, client: TestClient, user_headers: dict[str, str]) -> None:
        for index in range(5):
            create_summary(client, user_headers, f"Report {index}")

        page_one = client.get("/api/history?page=1&page_size=2", headers=user_headers).json()
        page_two = client.get("/api/history?page=2&page_size=2", headers=user_headers).json()

        assert page_one["total"] == 5
        assert page_one["pages"] == 3
        assert len(page_one["items"]) == 2
        assert page_one["items"][0]["id"] != page_two["items"][0]["id"]

    def test_rejects_an_out_of_range_page_size(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        assert client.get("/api/history?page_size=500", headers=user_headers).status_code == 422
        assert client.get("/api/history?page=0", headers=user_headers).status_code == 422

    def test_shows_only_the_callers_summaries(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        create_summary(client, user_headers, "Mine")
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))
        create_summary(client, other_headers, "Theirs")

        response = client.get("/api/history", headers=user_headers).json()

        assert response["total"] == 1
        assert response["items"][0]["title"] == "Mine"

    def test_requires_authentication(self, client: TestClient) -> None:
        assert client.get("/api/history").status_code == 401


class TestSearchHistory:
    def test_matches_the_title(self, client: TestClient, user_headers: dict[str, str]) -> None:
        create_summary(client, user_headers, "Quarterly finance review")
        create_summary(client, user_headers, "Machine learning roadmap")

        response = client.get("/api/history?search=finance", headers=user_headers).json()

        assert response["total"] == 1
        assert response["items"][0]["title"] == "Quarterly finance review"

    def test_is_case_insensitive(self, client: TestClient, user_headers: dict[str, str]) -> None:
        create_summary(client, user_headers, "Quarterly Finance Review")

        response = client.get("/api/history?search=FINANCE", headers=user_headers).json()

        assert response["total"] == 1

    def test_matches_the_original_text(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        create_summary(client, user_headers, "Untitled report")

        response = client.get("/api/history?search=abstractive", headers=user_headers).json()

        assert response["total"] == 1

    def test_returns_an_empty_page_when_nothing_matches(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        create_summary(client, user_headers, "Quarterly finance review")

        response = client.get("/api/history?search=zzzzznotfound", headers=user_headers).json()

        assert response["total"] == 0
        assert response["items"] == []


class TestDeleteHistory:
    def test_deletes_the_summary_and_its_request(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        summary_id = create_summary(client, user_headers, "Disposable")

        response = client.delete(f"/api/history/{summary_id}", headers=user_headers)

        assert response.status_code == 200
        assert client.get(f"/api/history/{summary_id}", headers=user_headers).status_code == 404
        # No orphaned rows are left behind.
        assert db.query(Summary).count() == 0
        assert db.query(SummaryRequest).count() == 0

    def test_another_user_cannot_delete_it(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        summary_id = create_summary(client, user_headers, "Protected")
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))

        response = client.delete(f"/api/history/{summary_id}", headers=other_headers)

        assert response.status_code == 404
        assert client.get(f"/api/history/{summary_id}", headers=user_headers).status_code == 200

    def test_returns_404_for_an_unknown_id(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.delete(
            "/api/history/00000000-0000-0000-0000-000000000000", headers=user_headers
        )
        assert response.status_code == 404
