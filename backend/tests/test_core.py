"""Unit tests for the cross-cutting helpers."""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import (
    INSECURE_ADMIN_PASSWORD,
    INSECURE_JWT_SECRET,
    MIN_PRODUCTION_SECRET_LENGTH,
    Settings,
)
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models import (
    Document,
    SummaryRequest,
    UsageMetric,
    User,
)
from app.utils.file_utils import matches_magic_bytes, sanitize_filename
from app.utils.text_utils import chunk_text, normalize_text, preview, word_count


class TestPasswordHashing:
    def test_round_trips(self) -> None:
        hashed = hash_password("Password123")

        assert hashed != "Password123"
        assert verify_password("Password123", hashed)
        assert not verify_password("Password124", hashed)

    def test_salts_are_unique(self) -> None:
        assert hash_password("same") != hash_password("same")

    def test_handles_passwords_longer_than_the_bcrypt_limit(self) -> None:
        # bcrypt truncates at 72 bytes; the SHA-256 pre-hash must prevent two
        # different long passwords from colliding.
        first = "A" * 80 + "1"
        second = "A" * 80 + "2"
        hashed = hash_password(first)

        assert verify_password(first, hashed)
        assert not verify_password(second, hashed)

    def test_rejects_a_malformed_hash(self) -> None:
        assert not verify_password("Password123", "not-a-bcrypt-hash")


class TestTokens:
    def test_round_trips_claims(self) -> None:
        token, expires_at, jti = create_access_token("user-1", role="admin")
        claims = decode_access_token(token)

        assert claims["sub"] == "user-1"
        assert claims["role"] == "admin"
        assert claims["jti"] == jti
        assert claims["exp"] == int(expires_at.timestamp())

    def test_rejects_an_expired_token(self) -> None:
        token, _, _ = create_access_token(
            "user-1", role="user", expires_delta=timedelta(seconds=-10)
        )

        with pytest.raises(AuthenticationError):
            decode_access_token(token)

    def test_rejects_a_tampered_token(self) -> None:
        token, _, _ = create_access_token("user-1", role="user")

        with pytest.raises(AuthenticationError):
            decode_access_token(token[:-4] + "AAAA")


class TestFilenameSafety:
    @pytest.mark.parametrize(
        ("raw", "forbidden"),
        [
            ("../../../etc/passwd", "/"),
            ("..\\..\\windows\\system32\\cmd.exe", "\\"),
            ("/absolute/path/report.pdf", "/"),
        ],
    )
    def test_strips_directory_components(self, raw: str, forbidden: str) -> None:
        assert forbidden not in sanitize_filename(raw)

    def test_keeps_a_usable_name(self) -> None:
        assert sanitize_filename("Quarterly Report 2026.pdf") == "Quarterly_Report_2026.pdf"

    def test_never_returns_an_empty_name(self) -> None:
        assert sanitize_filename("...") == "upload"

    def test_checks_magic_bytes(self) -> None:
        assert matches_magic_bytes("pdf", b"%PDF-1.7 ...")
        assert not matches_magic_bytes("pdf", b"PK\x03\x04")
        assert matches_magic_bytes("docx", b"PK\x03\x04")
        assert matches_magic_bytes("txt", b"anything at all")


class TestTextUtils:
    def test_normalizes_whitespace_and_hyphenation(self) -> None:
        assert normalize_text("word-\nbreak   here\n\n\n\nnext") == "wordbreak here\n\nnext"

    def test_counts_words(self) -> None:
        assert word_count("one two three") == 3
        assert word_count("") == 0

    def test_truncates_a_preview_with_an_ellipsis(self) -> None:
        assert preview("word " * 100, 20).endswith("\u2026")
        assert preview("short text", 40) == "short text"

    def test_chunks_respect_the_word_budget(self) -> None:
        text = " ".join(f"Sentence number {index} carries some content." for index in range(60))

        chunks = chunk_text(text, max_words=40)

        assert len(chunks) > 1
        assert all(len(chunk.split()) <= 40 for chunk in chunks)

    def test_chunks_split_an_oversized_sentence(self) -> None:
        chunks = chunk_text("word " * 100, max_words=30)

        assert len(chunks) == 4
        assert all(len(chunk.split()) <= 30 for chunk in chunks)

    def test_short_text_stays_in_one_chunk(self) -> None:
        assert chunk_text("One short sentence.", max_words=100) == ["One short sentence."]

    def test_rejects_a_non_positive_budget(self) -> None:
        with pytest.raises(ValueError, match="max_words"):
            chunk_text("anything", max_words=0)


class TestProductionSafetyGuard:
    """Insecure defaults must never reach a production deployment."""

    @staticmethod
    def _settings(**overrides: object) -> Settings:
        base = {
            "environment": "production",
            "jwt_secret_key": "x" * MIN_PRODUCTION_SECRET_LENGTH,
            "admin_password": "A-Strong-Admin-Password-1",
            "cors_origins": "https://app.example.com",
        }
        return Settings(**{**base, **overrides})

    def test_a_correctly_configured_deployment_reports_no_problems(self) -> None:
        assert self._settings().insecure_production_settings() == []

    def test_rejects_the_default_jwt_secret(self) -> None:
        problems = self._settings(jwt_secret_key=INSECURE_JWT_SECRET).insecure_production_settings()

        assert any("JWT_SECRET_KEY" in problem for problem in problems)

    def test_rejects_a_short_jwt_secret(self) -> None:
        problems = self._settings(jwt_secret_key="tooshort").insecure_production_settings()

        assert any("at least" in problem for problem in problems)

    def test_rejects_the_default_admin_password(self) -> None:
        problems = self._settings(
            seed_admin=True, admin_password=INSECURE_ADMIN_PASSWORD
        ).insecure_production_settings()

        assert any("ADMIN_PASSWORD" in problem for problem in problems)

    def test_ignores_the_admin_password_when_seeding_is_disabled(self) -> None:
        problems = self._settings(
            seed_admin=False, admin_password=INSECURE_ADMIN_PASSWORD
        ).insecure_production_settings()

        assert problems == []

    def test_rejects_wildcard_cors(self) -> None:
        problems = self._settings(cors_origins="*").insecure_production_settings()

        assert any("CORS_ORIGINS" in problem for problem in problems)

    def test_rejects_s3_without_a_bucket(self) -> None:
        problems = self._settings(storage_backend="s3", s3_bucket=None)

        assert any("S3_BUCKET" in problem for problem in problems.insecure_production_settings())


class TestEnumPersistence:
    """Enum columns must persist lowercase values, not member names.

    ``database/schema.sql`` constrains these columns with lowercase CHECK lists
    (``role IN ('user', 'admin')``). SQLAlchemy defaults to storing member
    names, so without ``values_callable`` every insert is rejected by
    PostgreSQL even though a SQLite-generated schema accepts it.
    """

    @pytest.mark.parametrize(
        ("model", "attribute", "expected"),
        [
            (User, "role", {"user", "admin"}),
            (Document, "file_type", {"pdf", "docx", "txt"}),
            (SummaryRequest, "summary_length", {"short", "medium", "long"}),
            (SummaryRequest, "source_type", {"text", "document"}),
            (SummaryRequest, "status", {"pending", "completed", "failed"}),
            (UsageMetric, "metric_type", {"login", "registration", "feedback"}),
        ],
    )
    def test_columns_store_lowercase_values(
        self, model: type, attribute: str, expected: set[str]
    ) -> None:
        column = model.__table__.c[attribute]

        assert expected.issubset(set(column.type.enums)), column.type.enums


class TestSystemEndpoints:
    def test_health_reports_the_database_and_model(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "connected"
        assert body["environment"] == "test"

    def test_openapi_schema_is_generated(self, client: TestClient) -> None:
        response = client.get("/openapi.json")

        assert response.status_code == 200
        paths = response.json()["paths"]
        for expected in (
            "/api/auth/register",
            "/api/auth/login",
            "/api/documents/upload",
            "/api/summaries/text",
            "/api/history",
            "/api/feedback",
            "/api/admin/users",
        ):
            assert expected in paths, expected

    def test_every_response_carries_a_request_id(self, client: TestClient) -> None:
        response = client.get("/health")

        assert response.headers["X-Request-ID"]
        assert float(response.headers["X-Process-Time"]) >= 0

    def test_unknown_routes_return_the_shared_error_shape(self, client: TestClient) -> None:
        response = client.get("/api/does-not-exist")

        assert response.status_code == 404
        assert set(response.json()) == {"code", "message", "details", "request_id"}
