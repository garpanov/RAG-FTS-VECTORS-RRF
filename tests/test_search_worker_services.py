from collections.abc import Callable
from typing import cast

import pytest

from search_worker.repositories import ChunkMatch
from search_worker.services import ChunkSearchService
from search_worker.unit_of_work import SearchUnitOfWork


class StubEmbedder:
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions
        self.texts: list[str] | None = None

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[0.5] * self.dimensions]


class StubChunks:
    def __init__(self) -> None:
        self.embedding: list[float] | None = None
        self.limit: int | None = None

    async def find_nearest(self, embedding: list[float], limit: int) -> list[ChunkMatch]:
        self.embedding = embedding
        self.limit = limit
        return [ChunkMatch(1, "001-A", 0, "content", 0.1)]


class StubUnitOfWork:
    def __init__(self, chunks: StubChunks) -> None:
        self.chunks = chunks

    async def __aenter__(self) -> StubUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


def make_uow_factory(chunks: StubChunks) -> Callable[[], SearchUnitOfWork]:
    return lambda: cast(SearchUnitOfWork, StubUnitOfWork(chunks))


@pytest.mark.asyncio
async def test_search_embeds_question_and_limits_results_to_three() -> None:
    chunks = StubChunks()
    embedder = StubEmbedder()
    service = ChunkSearchService(make_uow_factory(chunks), embedder)

    matches = await service.search("question", limit=10)

    assert embedder.texts == ["question"]
    assert chunks.embedding == [0.5] * 1024
    assert chunks.limit == 3
    assert matches[0].content == "content"


@pytest.mark.asyncio
async def test_search_rejects_wrong_embedding_dimension() -> None:
    service = ChunkSearchService(make_uow_factory(StubChunks()), StubEmbedder(dimensions=10))

    with pytest.raises(ValueError, match="1024"):
        await service.search("question")
