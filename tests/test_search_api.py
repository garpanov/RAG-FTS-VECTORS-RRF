from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.dependencies import get_search_service
from app.main import app
from app.search_client import (
    FtsSearchChunk,
    RerankedSearchChunk,
    SearchChunk,
    SearchWorkerUnavailableError,
)


class StubSearchService:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.question: str | None = None

    async def search(self, question: str) -> list[SearchChunk]:
        self.question = question
        if self.unavailable:
            raise SearchWorkerUnavailableError
        return [
            SearchChunk(
                document_id=42,
                document_number="001-A",
                chunk_number=1,
                content="closest chunk",
                distance=0.125,
            )
        ]

    async def rerank(self, question: str) -> list[RerankedSearchChunk]:
        self.question = question
        if self.unavailable:
            raise SearchWorkerUnavailableError
        return [
            RerankedSearchChunk(
                document_id=42,
                document_number="001-A",
                chunk_number=1,
                content="reranked chunk",
                distance=0.125,
                reranker_score=0.95,
            )
        ]

    async def search_fts(self, question: str) -> list[FtsSearchChunk]:
        self.question = question
        if self.unavailable:
            raise SearchWorkerUnavailableError
        return [
            FtsSearchChunk(
                document_id=42,
                document_number="001-A",
                chunk_number=1,
                content="full-text chunk",
                rank=0.75,
            )
        ]


@pytest.fixture
def search_service() -> Generator[StubSearchService]:
    service = StubSearchService()
    app.dependency_overrides[get_search_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_search_returns_chunks(search_service: StubSearchService) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={"question": "  my question  "})

    assert response.status_code == 200
    assert response.json() == {
        "chunks": [
            {
                "document_id": 42,
                "document_number": "001-A",
                "chunk_number": 1,
                "content": "closest chunk",
                "distance": 0.125,
            }
        ]
    }
    assert search_service.question == "my question"


@pytest.mark.asyncio
async def test_search_rejects_blank_question(search_service: StubSearchService) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/search", json={"question": "   "})

    assert response.status_code == 422
    assert search_service.question is None


@pytest.mark.asyncio
async def test_search_returns_service_unavailable() -> None:
    app.dependency_overrides[get_search_service] = lambda: StubSearchService(unavailable=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/search", json={"question": "question"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_fts_returns_ranked_chunks(search_service: StubSearchService) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/fts", json={"question": "  exact words  "})

    assert response.status_code == 200
    assert response.json() == {
        "chunks": [
            {
                "document_id": 42,
                "document_number": "001-A",
                "chunk_number": 1,
                "content": "full-text chunk",
                "rank": 0.75,
            }
        ]
    }
    assert search_service.question == "exact words"


@pytest.mark.asyncio
async def test_fts_returns_service_unavailable() -> None:
    app.dependency_overrides[get_search_service] = lambda: StubSearchService(unavailable=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/fts", json={"question": "question"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_reranker_returns_reranked_chunks(search_service: StubSearchService) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/reranker", json={"question": "  my question  "})

    assert response.status_code == 200
    assert response.json() == {
        "chunks": [
            {
                "document_id": 42,
                "document_number": "001-A",
                "chunk_number": 1,
                "content": "reranked chunk",
                "distance": 0.125,
                "reranker_score": 0.95,
            }
        ]
    }
    assert search_service.question == "my question"


@pytest.mark.asyncio
async def test_reranker_returns_service_unavailable() -> None:
    app.dependency_overrides[get_search_service] = lambda: StubSearchService(unavailable=True)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post("/reranker", json={"question": "question"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
