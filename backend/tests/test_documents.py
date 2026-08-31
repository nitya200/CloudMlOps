"""Document upload API tests (UC-05)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import auth_header, create_user, login
from tests.factories import build_docx_bytes, build_pdf_bytes, build_txt_bytes


def upload(client: TestClient, headers: dict[str, str], name: str, data: bytes, mime: str):
    return client.post("/api/documents/upload", files={"file": (name, data, mime)}, headers=headers)


class TestUpload:
    def test_uploads_a_pdf(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = upload(
            client, user_headers, "report.pdf", build_pdf_bytes(pages=2), "application/pdf"
        )

        assert response.status_code == 201
        body = response.json()
        assert body["file_type"] == "pdf"
        assert body["page_count"] == 2
        assert body["word_count"] > 0
        assert body["text_preview"]

    def test_uploads_a_docx(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = upload(
            client,
            user_headers,
            "review.docx",
            build_docx_bytes(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        assert response.status_code == 201
        assert response.json()["file_type"] == "docx"

    def test_uploads_a_txt(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = upload(client, user_headers, "notes.txt", build_txt_bytes(), "text/plain")

        assert response.status_code == 201
        assert response.json()["file_type"] == "txt"

    def test_rejects_an_unsupported_extension(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = upload(client, user_headers, "malware.exe", b"MZ\x90\x00", "application/exe")

        assert response.status_code == 415
        assert response.json()["code"] == "unsupported_file_type"

    def test_rejects_a_file_whose_bytes_do_not_match_its_extension(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        # A ZIP archive renamed to .pdf must not be accepted.
        response = upload(client, user_headers, "fake.pdf", b"PK\x03\x04rest", "application/pdf")

        assert response.status_code == 415

    def test_rejects_binary_content_disguised_as_text(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = upload(
            client, user_headers, "sneaky.txt", b"\x00\x01\x02\x03" * 64, "text/plain"
        )

        assert response.status_code == 415

    def test_rejects_an_empty_file(self, client: TestClient, user_headers: dict[str, str]) -> None:
        response = upload(client, user_headers, "empty.txt", b"", "text/plain")

        assert response.status_code == 422

    def test_rejects_a_file_over_the_size_limit(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        oversized = b"word " * (6 * 1024 * 1024 // 5)  # ~6 MB against a 5 MB limit

        response = upload(client, user_headers, "big.txt", oversized, "text/plain")

        assert response.status_code == 413
        assert response.json()["code"] == "payload_too_large"

    def test_rejects_a_scanned_pdf_with_no_text_layer(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        import pymupdf

        document = pymupdf.open()
        document.new_page()  # a blank page has no extractable text
        data = document.tobytes()
        document.close()

        response = upload(client, user_headers, "scan.pdf", data, "application/pdf")

        assert response.status_code == 422
        assert response.json()["code"] == "extraction_failed"

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post(
            "/api/documents/upload", files={"file": ("a.txt", build_txt_bytes(), "text/plain")}
        )
        assert response.status_code == 401

    def test_sanitizes_a_path_traversal_filename(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = upload(
            client, user_headers, "../../../../etc/passwd.txt", build_txt_bytes(), "text/plain"
        )

        assert response.status_code == 201
        assert "/" not in response.json()["filename"]


class TestDocumentAccess:
    def test_lists_only_the_callers_documents(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        upload(client, user_headers, "mine.txt", build_txt_bytes(), "text/plain")
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))
        upload(client, other_headers, "theirs.txt", build_txt_bytes(), "text/plain")

        response = client.get("/api/documents", headers=user_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["filename"] == "mine.txt"

    def test_another_user_cannot_read_a_document(
        self, client: TestClient, db: Session, user_headers: dict[str, str]
    ) -> None:
        document_id = upload(
            client, user_headers, "secret.txt", build_txt_bytes(), "text/plain"
        ).json()["id"]
        other = create_user(db, email="other@example.com", password="Password123")
        other_headers = auth_header(login(client, other.email, "Password123"))

        response = client.get(f"/api/documents/{document_id}", headers=other_headers)

        # 404 rather than 403 so the endpoint does not confirm the id exists.
        assert response.status_code == 404

    def test_deletes_a_document(self, client: TestClient, user_headers: dict[str, str]) -> None:
        document_id = upload(
            client, user_headers, "temp.txt", build_txt_bytes(), "text/plain"
        ).json()["id"]

        assert (
            client.delete(f"/api/documents/{document_id}", headers=user_headers).status_code == 200
        )
        assert client.get(f"/api/documents/{document_id}", headers=user_headers).status_code == 404

    def test_reports_supported_types(self, client: TestClient) -> None:
        response = client.get("/api/documents/supported-types")

        assert response.status_code == 200
        assert set(response.json()["types"]) == {"pdf", "docx", "txt"}
