from collections.abc import Callable
from typing import Protocol

from search_worker.repositories import ChunkMatch
from search_worker.unit_of_work import SearchUnitOfWork


class Embedder(Protocol):
    async def embed_query(self, texts: list[str]) -> list[list[float]]: ...


class ChunkSearchService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], SearchUnitOfWork],
        embedder: Embedder,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._embedder = embedder

    async def search(self, question: str, limit: int = 3) -> list[ChunkMatch]:
        embeddings = await self._embedder.embed_query([question])
        if len(embeddings) != 1 or len(embeddings[0]) != 1024:
            raise ValueError("Question embedding must contain 1024 dimensions")

        async with self._unit_of_work_factory() as unit_of_work:
            return await unit_of_work.chunks.find_nearest(embeddings[0], min(limit, 3))
