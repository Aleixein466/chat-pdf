from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db


class FakeSession:
    def __init__(self) -> None:
        self._document_id = 0
        self.objects: list[object] = []

    def add(self, instance: object) -> None:
        if instance.__class__.__name__ == "Document" and getattr(instance, "id", None) is None:
            self._document_id += 1
            instance.id = self._document_id
        self.objects.append(instance)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        return None

    def refresh(self, instance: object) -> None:
        return None

    def close(self) -> None:
        return None


@pytest.fixture
def fake_db() -> FakeSession:
    return FakeSession()


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, fake_db: FakeSession) -> Generator[TestClient, None, None]:
    import app.main

    monkeypatch.setattr(app.main, "initialize_database", lambda: None)
    app.main.app.dependency_overrides[get_db] = lambda: fake_db

    with TestClient(app.main.app) as test_client:
        yield test_client

    app.main.app.dependency_overrides.clear()
