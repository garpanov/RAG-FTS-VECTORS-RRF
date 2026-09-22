from collections.abc import Callable
from typing import Protocol

from worker.chunking import MarkdownChunker
from worker.unit_of_work import WorkerUnitOfWork


class Embedder(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class DocumentProcessingService:
    def __init__(
        self,
        unit_of_work_factory: Callable[[], WorkerUnitOfWork],
        chunker: MarkdownChunker,
        embedder: Embedder,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._chunker = chunker
        self._embedder = embedder

    async def process(self, document_id: int) -> int | None:
        async with self._unit_of_work_factory() as unit_of_work:
            document = await unit_of_work.documents.get(document_id)
            if document is None:
                return None
            context = document.context

        chunks = self._chunker.split(context)
        embeddings = await self._embedder.embed(chunks)
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count does not match chunk count")
        if any(len(embedding) != 1024 for embedding in embeddings):
            raise ValueError("Each embedding must contain 1024 dimensions")

        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.chunks.replace(document_id, chunks, embeddings)

        return len(chunks)
