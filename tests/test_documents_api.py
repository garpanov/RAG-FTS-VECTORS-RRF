from collections.abc import Generator
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_document_service
from app.main import app
from app.services import DocumentAlreadyExistsError


class StubDocumentService:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.received: tuple[str, str] | None = None

    async def create_document(self, document_number: str, context: str) -> Any:
        self.received = (document_number, context)
        if self.duplicate:
            raise DocumentAlreadyExistsError(document_number)
        return SimpleNamespace(
            id=1,
            document_number=document_number,
            context=context,
            created_at=datetime(2026, 9, 20, tzinfo=UTC),
        )


@pytest.fixture
def service() -> Generator[StubDocumentService]:
    stub = StubDocumentService()
    app.dependency_overrides[get_document_service] = lambda: stub
    yield stub
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_document_returns_created_record(service: StubDocumentService) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/documents",
            json={"document_number": " 001-A ", "context": "  original context  "},
        )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "document_number": "001-A",
        "context": "  original context  ",
        "created_at": "2026-09-20T00:00:00Z",
    }
    assert service.received == ("001-A", "  original context  ")


@pytest.mark.asyncio
async def test_create_document_returns_conflict_for_duplicate() -> None:
    app.dependency_overrides[get_document_service] = lambda: StubDocumentService(duplicate=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/documents",
                json={"document_number": "001-A", "context": "context"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"document_number": "", "context": "context"},
        {"document_number": "   ", "context": "context"},
        {"document_number": "001-A", "context": ""},
        {"document_number": "001-A", "context": "   "},
    ],
)
async def test_create_document_rejects_blank_values(payload: dict[str, str]) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/documents", json=payload)

    assert response.status_code == 422
