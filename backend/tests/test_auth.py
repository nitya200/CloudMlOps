"""Authentication and authorization tests (UC-01, UC-02, UC-03)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.rate_limit import SlidingWindowRateLimiter
from tests.conftest import auth_header, create_user, login

REGISTRATION = {
    "name": "Aakash Malipeddi",
    "email": "Aakash@Example.com",
    "password": "StrongPass123",
}


class TestRegistration:
    def test_registers_a_new_user(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json=REGISTRATION)

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "aakash@example.com"  # normalized to lower case
        assert body["role"] == "user"
        assert body["is_active"] is True
        assert "password" not in body and "password_hash" not in body

    def test_rejects_duplicate_email_case_insensitively(self, client: TestClient) -> None:
        client.post("/api/auth/register", json=REGISTRATION)

        response = client.post(
            "/api/auth/register", json={**REGISTRATION, "email": "AAKASH@example.com"}
        )

        assert response.status_code == 409
        assert response.json()["code"] == "conflict"

    def test_rejects_password_without_a_digit(self, client: TestClient) -> None:
        response = client.post(
            "/api/auth/register", json={**REGISTRATION, "password": "onlyletters"}
        )
        assert response.status_code == 422

    def test_rejects_short_password(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json={**REGISTRATION, "password": "Ab1"})
        assert response.status_code == 422

    def test_rejects_malformed_email(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json={**REGISTRATION, "email": "not-an-email"})
        assert response.status_code == 422

    def test_new_accounts_cannot_self_assign_admin(self, client: TestClient) -> None:
        response = client.post("/api/auth/register", json={**REGISTRATION, "role": "admin"})

        assert response.status_code == 201
        assert response.json()["role"] == "user"


class TestLogin:
    def test_returns_a_token_and_profile(self, client: TestClient, db: Session) -> None:
        create_user(db, email="login@example.com", password="Password123")

        response = client.post(
            "/api/auth/login", json={"email": "login@example.com", "password": "Password123"}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
        assert body["user"]["email"] == "login@example.com"

    def test_rejects_wrong_password(self, client: TestClient, db: Session) -> None:
        create_user(db, email="login@example.com", password="Password123")

        response = client.post(
            "/api/auth/login", json={"email": "login@example.com", "password": "WrongPass123"}
        )

        assert response.status_code == 401

    def test_unknown_email_is_indistinguishable_from_a_wrong_password(
        self, client: TestClient, db: Session
    ) -> None:
        create_user(db, email="login@example.com", password="Password123")

        wrong_password = client.post(
            "/api/auth/login", json={"email": "login@example.com", "password": "WrongPass123"}
        )
        unknown_email = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "Password123"}
        )

        # Identical responses prevent account enumeration.
        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json()["message"] == unknown_email.json()["message"]

    def test_rejects_deactivated_account(self, client: TestClient, db: Session) -> None:
        create_user(db, email="off@example.com", password="Password123", is_active=False)

        response = client.post(
            "/api/auth/login", json={"email": "off@example.com", "password": "Password123"}
        )

        assert response.status_code == 403


class TestCurrentUser:
    def test_returns_the_authenticated_profile(
        self, client: TestClient, user_headers: dict[str, str]
    ) -> None:
        response = client.get("/api/auth/me", headers=user_headers)

        assert response.status_code == 200
        assert response.json()["email"] == "user@example.com"

    def test_requires_a_token(self, client: TestClient) -> None:
        assert client.get("/api/auth/me").status_code == 401

    def test_rejects_a_garbage_token(self, client: TestClient) -> None:
        response = client.get("/api/auth/me", headers=auth_header("not.a.jwt"))
        assert response.status_code == 401


class TestRateLimiting:
    """Brute-force protection on the credential endpoints."""

    def test_blocks_repeated_login_attempts(self, client: TestClient, db: Session) -> None:
        create_user(db, email="target@example.com", password="Password123")
        payload = {"email": "target@example.com", "password": "WrongPassword1"}

        for _ in range(settings.login_rate_limit):
            assert client.post("/api/auth/login", json=payload).status_code == 401

        response = client.post("/api/auth/login", json=payload)

        assert response.status_code == 429
        assert response.json()["code"] == "rate_limited"
        assert int(response.headers["Retry-After"]) > 0

    def test_the_block_applies_to_correct_credentials_too(
        self, client: TestClient, db: Session
    ) -> None:
        # Otherwise an attacker learns a password is right from the status code.
        create_user(db, email="target@example.com", password="Password123")
        wrong = {"email": "target@example.com", "password": "WrongPassword1"}

        for _ in range(settings.login_rate_limit):
            client.post("/api/auth/login", json=wrong)

        response = client.post(
            "/api/auth/login", json={"email": "target@example.com", "password": "Password123"}
        )

        assert response.status_code == 429

    def test_limits_registration_separately_from_login(self, client: TestClient) -> None:
        for index in range(settings.register_rate_limit):
            response = client.post(
                "/api/auth/register",
                json={
                    "name": "Someone",
                    "email": f"user{index}@example.com",
                    "password": "Password123",
                },
            )
            assert response.status_code == 201

        blocked = client.post(
            "/api/auth/register",
            json={"name": "Someone", "email": "last@example.com", "password": "Password123"},
        )
        assert blocked.status_code == 429
        # Login has its own budget and must be unaffected.
        assert (
            client.post(
                "/api/auth/login", json={"email": "user0@example.com", "password": "Password123"}
            ).status_code
            == 200
        )

    def test_expired_hits_leave_the_window(self) -> None:
        window = SlidingWindowRateLimiter()

        assert window.hit("k", limit=1, window_seconds=60) is None
        retry_after = window.hit("k", limit=1, window_seconds=60)
        assert retry_after is not None and retry_after > 0

        # A zero-length window means every previous hit has already aged out.
        assert window.hit("k", limit=1, window_seconds=0) is None

    def test_keys_are_independent(self) -> None:
        window = SlidingWindowRateLimiter()

        assert window.hit("a", limit=1, window_seconds=60) is None
        assert window.hit("b", limit=1, window_seconds=60) is None
        assert window.hit("a", limit=1, window_seconds=60) is not None


class TestLogout:
    def test_revokes_the_token_server_side(self, client: TestClient, db: Session) -> None:
        create_user(db, email="bye@example.com", password="Password123")
        headers = auth_header(login(client, "bye@example.com", "Password123"))

        assert client.get("/api/auth/me", headers=headers).status_code == 200
        assert client.post("/api/auth/logout", headers=headers).status_code == 200
        # The same token must stop working once the session is revoked.
        assert client.get("/api/auth/me", headers=headers).status_code == 401

    def test_requires_a_token(self, client: TestClient) -> None:
        assert client.post("/api/auth/logout").status_code == 401
