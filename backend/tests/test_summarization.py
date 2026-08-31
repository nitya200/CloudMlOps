"""Summarization tests (UC-04, UC-06, UC-07, UC-08, UC-09)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.extractive import ExtractiveSummarizer
from app.ai.factory import set_summarizer
from app.ai.prompts import (
    LongSummaryStrategy,
    MediumSummaryStrategy,
    ShortSummaryStrategy,
    SummaryStrategyFactory,
)
from app.core.exceptions import ValidationError
from app.models import RequestStatus, SummaryLength, SummaryRequest
from tests.conftest import LONG_TEXT, FailingSummarizer, auth_header, create_user, login
from tests.factories import build_pdf_bytes, long_text


class TestStrategyFactory:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("short", ShortSummaryStrategy),
            ("medium", MediumSummaryStrategy),
            ("long", LongSummaryStrategy),
            (SummaryLength.SHORT, ShortSummaryStrategy),
        ],
    )
    def test_resolves_each_length(self, value, expected) -> None:
        assert isinstance(SummaryStrategyFactory.create(value), expected)

    def test_rejects_an_unknown_length(self) -> None:
        with pytest.raises(ValidationError):
            SummaryStrategyFactory.create("gigantic")

    def test_longer_summaries_allow_more_tokens(self) -> None:
        short = SummaryStrategyFactory.create("short").params.max_new_tokens
        medium = SummaryStrategyFactory.create("medium").params.max_new_tokens
        long_ = SummaryStrategyFactory.create("long").params.max_new_tokens

        assert short < medium < long_

    def test_prompt_contains_the_instruction_and_the_text(self) -> None:
        prompt = SummaryStrategyFactory.create("short").build_prompt("Some document text.")

        assert "2 to 3 sentences" in prompt
        assert "Some document text." in prompt


class TestExtractiveFallback:
    """The fallback backend must work with no AI wheels installed."""

    def test_compresses_a_long_document(self) -> None:
        source = long_text(6)

        output = ExtractiveSummarizer().summarize(source, MediumSummaryStrategy())

        assert output.backend == "extractive"
        assert output.summary_text
        assert len(output.summary_text) < len(source)

    def test_returns_sentences_taken_from_the_source(self) -> None:
        output = ExtractiveSummarizer().summarize(LONG_TEXT, ShortSummaryStrategy())

        # Extractive summarization must not invent text.
        assert output.summary_text
        for sentence in output.summary_text.split(". "):
            assert sentence.strip(". ") in LONG_TEXT

    def test_shorter_strategy_produces_a_shorter_summary(self) -> None:
        summarizer = ExtractiveSummarizer()
        short = summarizer.summarize(long_text(), ShortSummaryStrategy())
        long_summary = summarizer.summarize(long_text(), LongSummaryStrategy())

        assert len(short.summary_text.split()) <= len(long_summary.summary_text.split())


class TestSummarizeText:
    def test_creates_a_summary(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = client.post(
            "/api/summaries/text",
            json={"text": LONG_TEXT, "summary_length": "short", "title": "AI adoption"},
            headers=user_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["summary_text"]
        assert body["word_count"] > 0
        assert body["processing_time_seconds"] >= 0
        assert body["backend"] == "stub"

    def test_persists_the_request_and_its_status(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        client.post(
            "/api/summaries/text",
            json={"text": LONG_TEXT, "summary_length": "medium"},
            headers=user_headers,
        )

        request = db.query(SummaryRequest).one()
        assert request.status == RequestStatus.COMPLETED
        assert request.input_word_count > 0
        assert request.summary_length == SummaryLength.MEDIUM

    def test_derives_a_title_when_none_is_given(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        summary_id = client.post(
            "/api/summaries/text", json={"text": LONG_TEXT}, headers=user_headers
        ).json()["id"]

        detail = client.get(f"/api/summaries/{summary_id}", headers=user_headers).json()
        assert detail["title"].startswith("Artificial intelligence")

    def test_rejects_text_that_is_too_short(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/summaries/text", json={"text": "Too short."}, headers=user_headers
        )
        assert response.status_code == 422

    def test_rejects_blank_text(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = client.post(
            "/api/summaries/text", json={"text": " " * 400}, headers=user_headers
        )
        assert response.status_code == 422

    def test_rejects_an_invalid_summary_length(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/summaries/text",
            json={"text": LONG_TEXT, "summary_length": "enormous"},
            headers=user_headers,
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post("/api/summaries/text", json={"text": LONG_TEXT})
        assert response.status_code == 401

    def test_reports_a_model_failure_as_503_and_records_it(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        set_summarizer(FailingSummarizer())

        response = client.post(
            "/api/summaries/text", json={"text": LONG_TEXT}, headers=user_headers
        )

        assert response.status_code == 503
        assert response.json()["code"] == "summarization_failed"
        # The failed attempt is still auditable.
        request = db.query(SummaryRequest).one()
        assert request.status == RequestStatus.FAILED
        assert request.error_message


class TestSummarizeDocument:
    def test_summarizes_an_uploaded_document(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        document_id = client.post(
            "/api/documents/upload",
            files={"file": ("paper.pdf", build_pdf_bytes(pages=3), "application/pdf")},
            headers=user_headers,
        ).json()["id"]

        response = client.post(
            f"/api/summaries/document/{document_id}",
            json={"summary_length": "medium"},
            headers=user_headers,
        )

        assert response.status_code == 201
        assert response.json()["summary_text"]

    def test_returns_404_for_a_missing_document(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.post(
            "/api/summaries/document/00000000-0000-0000-0000-000000000000",
            json={"summary_length": "short"},
            headers=user_headers,
        )
        assert response.status_code == 404

    def test_cannot_summarize_another_users_document(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        document_id = client.post(
            "/api/documents/upload",
            files={"file": ("mine.pdf", build_pdf_bytes(), "application/pdf")},
            headers=user_headers,
        ).json()["id"]
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))

        response = client.post(
            f"/api/summaries/document/{document_id}",
            json={"summary_length": "short"},
            headers=other_headers,
        )

        assert response.status_code == 404


class TestSummaryRead:
    def test_returns_the_detail_view(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.get(f"/api/summaries/{summary_id}", headers=user_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["title"] == "Fixture summary"
        assert body["source_type"] == "text"
        assert body["input_preview"]
        assert body["my_rating"] is None

    def test_downloads_a_text_report(
        self, client: TestClient, user_headers: dict[str, str], summary_id: str
    ) -> None:
        response = client.get(f"/api/summaries/{summary_id}/download", headers=user_headers)

        assert response.status_code == 200
        assert "attachment" in response.headers["content-disposition"]
        assert "SUMMARY" in response.text
        assert "Fixture summary" in response.text

    def test_another_user_cannot_read_the_summary(
        self, client: TestClient, db: Session, summary_id: str
    ) -> None:
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))

        assert client.get(f"/api/summaries/{summary_id}", headers=other_headers).status_code == 404

    def test_lists_the_available_length_options(self, client: TestClient) -> None:
        response = client.get("/api/summaries/options")

        assert response.status_code == 200
        values = [item["value"] for item in response.json()["lengths"]]
        assert values == ["short", "medium", "long"]
