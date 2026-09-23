from collections.abc import Callable
from typing import cast

import pytest

from search_worker.repositories import ChunkMatch, FtsChunkMatch
from search_worker.services import ChunkSearchService
from search_worker.unit_of_work import SearchUnitOfWork


class StubEmbedder:
    def __init__(self, dimensions: int = 1024) -> None:
        self.dimensions = dimensions
        self.texts: list[str] | None = None

    async def embed_query(self, texts: list[str]) -> list[list[float]]:
        self.texts = texts
        return [[0.5] * self.dimensions]


class StubChunks:
    def __init__(
        self,
        matches: list[ChunkMatch] | None = None,
        fts_matches: list[FtsChunkMatch] | None = None,
    ) -> None:
        self.embedding: list[float] | None = None
        self.limit: int | None = None
        self.matches = (
            matches if matches is not None else [ChunkMatch(1, "001-A", 0, "content", 0.1)]
        )
        self.fts_matches = (
            fts_matches
            if fts_matches is not None
            else [FtsChunkMatch(1, "001-A", 0, "fts content", 0.75)]
        )
        self.fts_question: str | None = None
        self.fts_limit: int | None = None
        self.calls: list[str] = []

    async def find_nearest(self, embedding: list[float], limit: int) -> list[ChunkMatch]:
        self.calls.append("vector")
        self.embedding = embedding
        self.limit = limit
        return self.matches

    async def find_fts(self, question: str, limit: int) -> list[FtsChunkMatch]:
        self.calls.append("fts")
        self.fts_question = question
        self.fts_limit = limit
        return self.fts_matches


class StubReranker:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.question: str | None = None
        self.contents: list[str] | None = None

    async def rerank(self, question: str, chunks: list[str]) -> list[float]:
        self.question = question
        self.contents = chunks
        return self.scores


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
async def test_search_embeds_question_and_limits_results_to_thirty() -> None:
    chunks = StubChunks()
    embedder = StubEmbedder()
    service = ChunkSearchService(make_uow_factory(chunks), embedder)

    matches = await service.search("question", limit=100)

    assert embedder.texts == ["question"]
    assert chunks.embedding == [0.5] * 1024
    assert chunks.limit == 30
    assert matches[0].content == "content"


@pytest.mark.asyncio
async def test_search_rejects_wrong_embedding_dimension() -> None:
    service = ChunkSearchService(make_uow_factory(StubChunks()), StubEmbedder(dimensions=10))

    with pytest.raises(ValueError, match="1024"):
        await service.search("question")


@pytest.mark.asyncio
async def test_fts_search_limits_results_to_thirty_without_embedding() -> None:
    chunks = StubChunks()
    embedder = StubEmbedder()
    service = ChunkSearchService(make_uow_factory(chunks), embedder)

    matches = await service.search_fts("matching words", limit=100)

    assert chunks.fts_question == "matching words"
    assert chunks.fts_limit == 30
    assert embedder.texts is None
    assert matches[0].rank == 0.75


@pytest.mark.asyncio
async def test_rerank_retrieves_thirty_candidates_and_returns_top_five() -> None:
    candidates = [
        ChunkMatch(index, f"doc-{index}", index, f"content-{index}", index / 100)
        for index in range(6)
    ]
    chunks = StubChunks(candidates)
    reranker = StubReranker([0.1, 0.9, 0.2, 0.8, 0.3, 0.7])
    service = ChunkSearchService(make_uow_factory(chunks), StubEmbedder(), reranker)

    matches = await service.rerank("question")

    assert chunks.limit == 30
    assert reranker.question == "question"
    assert reranker.contents == [candidate.content for candidate in candidates]
    assert [match.chunk_number for match in matches] == [1, 3, 5, 4, 2]
    assert [match.reranker_score for match in matches] == [0.9, 0.8, 0.7, 0.3, 0.2]


@pytest.mark.asyncio
async def test_rerank_rejects_wrong_number_of_scores() -> None:
    service = ChunkSearchService(
        make_uow_factory(StubChunks()),
        StubEmbedder(),
        StubReranker([]),
    )

    with pytest.raises(ValueError, match="one score per chunk"):
        await service.rerank("question")


@pytest.mark.asyncio
async def test_hybrid_search_fuses_fts_and_vector_then_returns_top_five() -> None:
    vector_candidates = [
        ChunkMatch(index, f"doc-{index}", index, f"content-{index}", index / 100)
        for index in range(1, 7)
    ]
    fts_candidates = [
        FtsChunkMatch(2, "doc-2", 2, "content-2", 0.9),
        FtsChunkMatch(7, "doc-7", 7, "content-7", 0.8),
        FtsChunkMatch(1, "doc-1", 1, "content-1", 0.7),
    ]
    chunks = StubChunks(vector_candidates, fts_candidates)
    reranker = StubReranker([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])
    service = ChunkSearchService(make_uow_factory(chunks), StubEmbedder(), reranker)

    matches = await service.hybrid_search("question")

    assert chunks.calls == ["fts", "vector"]
    assert chunks.fts_limit == 30
    assert chunks.limit == 30
    assert reranker.contents == [
        "content-2",
        "content-1",
        "content-7",
        "content-3",
        "content-4",
        "content-5",
        "content-6",
    ]
    assert [match.chunk_number for match in matches] == [6, 5, 4, 3, 7]
    assert all(match.rrf_score > 0 for match in matches)


@pytest.mark.asyncio
async def test_hybrid_search_returns_empty_without_reranking() -> None:
    chunks = StubChunks(matches=[], fts_matches=[])
    reranker = StubReranker([])
    service = ChunkSearchService(make_uow_factory(chunks), StubEmbedder(), reranker)

    matches = await service.hybrid_search("question")

    assert matches == []
    assert reranker.contents is None
