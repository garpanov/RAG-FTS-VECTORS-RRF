from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from search_worker.repositories import ChunkMatch
from search_worker.unit_of_work import SearchUnitOfWork


class Embedder(Protocol):
    async def embed_query(self, texts: list[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    async def rerank(self, question: str, chunks: list[str]) -> list[float]: ...


@dataclass(frozen=True, slots=True)
class RerankedChunkMatch:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float
    reranker_score: float


class ChunkSearchService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SearchUnitOfWork],
        embedder: Embedder,
        reranker: Reranker | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._embedder = embedder
        self._reranker = reranker

    async def search(self, question: str, limit: int = 30) -> list[ChunkMatch]:
        embeddings = await self._embedder.embed_query([question])
        if len(embeddings) != 1 or len(embeddings[0]) != 1024:
            raise ValueError("Question embedding must contain 1024 dimensions")

        async with self._unit_of_work_factory() as unit_of_work:
            return await unit_of_work.chunks.find_nearest(embeddings[0], min(limit, 30))

    async def rerank(self, question: str) -> list[RerankedChunkMatch]:
        if self._reranker is None:
            raise RuntimeError("Reranker is not configured")

        candidates = await self.search(question, limit=30)
        if not candidates:
            return []

        scores = await self._reranker.rerank(
            question,
            [candidate.content for candidate in candidates],
        )
        if len(scores) != len(candidates):
            raise ValueError("Reranker must return one score per chunk")

        ranked = sorted(
            zip(candidates, scores, strict=True),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            RerankedChunkMatch(
                document_id=candidate.document_id,
                document_number=candidate.document_number,
                chunk_number=candidate.chunk_number,
                content=candidate.content,
                distance=candidate.distance,
                reranker_score=score,
            )
            for candidate, score in ranked[:5]
        ]
