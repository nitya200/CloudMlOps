"""Storage backend tests.

The S3 path is covered with a fake client rather than boto3/moto: the point is
that ``DocumentService`` talks to the abstraction correctly, not that Amazon's
SDK works.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.storage import LocalStorage, StorageBackend, create_storage, set_storage
from tests.factories import build_txt_bytes


class InMemoryStorage(StorageBackend):
    """Stands in for S3 so the tests need no network or credentials."""

    name = "memory"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []

    def save(self, key: str, data: bytes) -> str:
        self.objects[key] = data
        return key

    def load(self, key: str) -> bytes | None:
        return self.objects.get(key)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)
        self.deleted.append(key)


class TestLocalStorage:
    def test_round_trips_a_file(self, tmp_path: Path) -> None:
        storage = LocalStorage(tmp_path)

        key = storage.save("user/report.txt", b"hello")

        assert storage.load(key) == b"hello"
        assert (tmp_path / "user" / "report.txt").is_file()

    def test_load_returns_none_for_a_missing_key(self, tmp_path: Path) -> None:
        assert LocalStorage(tmp_path).load("nope.txt") is None

    def test_delete_is_idempotent(self, tmp_path: Path) -> None:
        storage = LocalStorage(tmp_path)
        storage.save("a.txt", b"x")

        storage.delete("a.txt")
        storage.delete("a.txt")  # must not raise

        assert storage.load("a.txt") is None

    def test_rejects_keys_that_escape_the_storage_root(self, tmp_path: Path) -> None:
        storage = LocalStorage(tmp_path / "root")

        with pytest.raises(ValueError, match="outside the storage root"):
            storage.save("../escaped.txt", b"x")


class TestStorageFactory:
    def test_defaults_to_local(self) -> None:
        assert create_storage().name == "local"


class TestDocumentServiceUsesTheBackend:
    """Uploads and deletes must go through whichever backend is configured."""

    @pytest.fixture(autouse=True)
    def _use_memory_storage(self):
        backend = InMemoryStorage()
        set_storage(backend)
        yield backend
        set_storage(None)

    def test_upload_writes_through_the_backend(
        self, client: TestClient, user_headers: dict[str, str], _use_memory_storage: InMemoryStorage
    ) -> None:
        response = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", build_txt_bytes(), "text/plain")},
            headers=user_headers,
        )

        assert response.status_code == 201
        assert len(_use_memory_storage.objects) == 1
        # Keyed per user so two people uploading the same filename cannot clash.
        key = next(iter(_use_memory_storage.objects))
        assert key.endswith("_notes.txt")
        assert "/" in key

    def test_delete_removes_the_object(
        self, client: TestClient, user_headers: dict[str, str], _use_memory_storage: InMemoryStorage
    ) -> None:
        created = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", build_txt_bytes(), "text/plain")},
            headers=user_headers,
        ).json()

        assert (
            client.delete(f"/api/documents/{created['id']}", headers=user_headers).status_code
            == 200
        )
        assert _use_memory_storage.objects == {}
        assert len(_use_memory_storage.deleted) == 1

    def test_delete_survives_a_storage_outage(
        self, client: TestClient, user_headers: dict[str, str], _use_memory_storage: InMemoryStorage
    ) -> None:
        created = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", build_txt_bytes(), "text/plain")},
            headers=user_headers,
        ).json()

        def explode(key: str) -> None:
            raise RuntimeError("S3 is unreachable")

        _use_memory_storage.delete = explode  # type: ignore[method-assign]

        # The row must still go, otherwise the user cannot ever remove it.
        assert (
            client.delete(f"/api/documents/{created['id']}", headers=user_headers).status_code
            == 200
        )
        assert (
            client.get(f"/api/documents/{created['id']}", headers=user_headers).status_code == 404
        )
