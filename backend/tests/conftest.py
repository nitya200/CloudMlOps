"""Shared pytest fixtures.

The environment is configured *before* importing the application so that the
cached ``Settings`` object points at an in-memory SQLite database and the
deterministic stub summarizer instead of the real FLAN-T5 weights.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

_STORAGE_DIR = tempfile.mkdtemp(prefix="cloudmlops-test-")

os.environ.update(
    ENVIRONMENT="test",
    DATABASE_URL="sqlite+pysqlite:///:memory:",
    JWT_SECRET_KEY="test-secret-key-not-used-in-production",
    ACCESS_TOKEN_EXPIRE_MINUTES="60",
    BCRYPT_ROUNDS="4",  # keeps hashing out of the critical path
    AI_BACKEND="extractive",
    AI_EAGER_LOAD="false",
    SEED_ADMIN="false",
    AUTO_CREATE_SCHEMA="false",
    STORAGE_DIR=_STORAGE_DIR,
    LOG_LEVEL="WARNING",
    MAX_UPLOAD_SIZE_MB="5",
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.ai.base import SummarizationOutput, Summarizer  # noqa: E402
from app.ai.factory import set_summarizer  # noqa: E402
from app.ai.prompts import SummaryLengthStrategy  # noqa: E402
from app.core.database import SessionLocal, engine, get_db  # noqa: E402
from app.core.rate_limit import limiter  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, User, UserRole  # noqa: E402

LONG_TEXT = (
    "Artificial intelligence is reshaping how large organizations handle their "
    "internal documentation. Analysts routinely receive reports that run to "
    "hundreds of pages, and reading each one end to end is no longer feasible. "
    "Abstractive summarization models such as FLAN-T5 can compress those "
    "reports into a few sentences that preserve the central argument. The "
    "resulting summaries let reviewers triage a backlog quickly and decide "
    "which documents deserve a full read. Adoption still depends on trust, so "
    "platforms must record who generated each summary, how long it took, and "
    "how users rated its quality. Those signals form the feedback loop that "
    "drives later model improvements and give administrators the evidence they "
    "need to justify continued investment in the system."
)


class StubSummarizer(Summarizer):
    """Deterministic summarizer so tests never load a transformer."""

    backend = "stub"
    calls = 0

    @property
    def model_name(self) -> str:
        return "stub-model"

    def summarize(self, text: str, strategy: SummaryLengthStrategy) -> SummarizationOutput:
        type(self).calls += 1
        words = text.split()
        return SummarizationOutput(
            summary_text=f"[{strategy.length}] " + " ".join(words[:20]),
            chunk_count=1,
            model_name=self.model_name,
            backend=self.backend,
            metadata={"stub": True},
        )


class FailingSummarizer(Summarizer):
    """Simulates a model outage for the error-handling tests."""

    backend = "failing"

    @property
    def model_name(self) -> str:
        return "failing-model"

    def summarize(self, text: str, strategy: SummaryLengthStrategy) -> SummarizationOutput:
        from app.core.exceptions import SummarizationError

        raise SummarizationError("The summarization model failed to process this text.")


@pytest.fixture(autouse=True)
def _fresh_database() -> Iterator[None]:
    """Give every test an empty schema so tests cannot leak into each other."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    set_summarizer(StubSummarizer())
    # The limiter is process-global; without this, logins from earlier tests
    # would count against later ones and fail them at random.
    limiter.reset()
    yield
    set_summarizer(None)
    limiter.reset()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """TestClient sharing the test's session, so writes are visible to asserts."""

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def create_user(
    db: Session,
    *,
    email: str = "user@example.com",
    password: str = "Password123",
    name: str = "Test User",
    role: UserRole = UserRole.USER,
    is_active: bool = True,
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    return user


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(db: Session) -> User:
    return create_user(db)


@pytest.fixture
def admin(db: Session) -> User:
    return create_user(
        db,
        email="admin@example.com",
        password="AdminPass123",
        name="Admin User",
        role=UserRole.ADMIN,
    )


@pytest.fixture
def user_headers(client: TestClient, user: User) -> dict[str, str]:
    return auth_header(login(client, user.email, "Password123"))


@pytest.fixture
def admin_headers(client: TestClient, admin: User) -> dict[str, str]:
    return auth_header(login(client, admin.email, "AdminPass123"))


@pytest.fixture
def summary_id(client: TestClient, user_headers: dict[str, str]) -> str:
    response = client.post(
        "/api/summaries/text",
        json={"text": LONG_TEXT, "summary_length": "medium", "title": "Fixture summary"},
        headers=user_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
