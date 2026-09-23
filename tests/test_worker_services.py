from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

import pytest

from worker.services import DocumentProcessingService
from worker.unit_of_work import WorkerUnitOfWork


class StubDocuments:
    def __init__(self, context: str | None) -> None:
        self._context = context

    async def get(self, document_id: int) -> Any:
        if self._context is None:
            return None
        return SimpleNamespace(id=document_id, context=self._context)


class StubChunks:
    def __init__(self) -> None:
        self.replaced: tuple[int, list[str], list[list[float]]] | None = None

    async def replace(
        self,
        document_id: int,
        contents: list[str],
        embeddings: list[list[float]],
    ) -> None:
        self.replaced = (document_id, contents, embeddings)


class StubUnitOfWork:
    def __init__(self, context: str | None, chunks: StubChunks) -> None:
        self.documents = StubDocuments(context)
        self.chunks = chunks

    async def __aenter__(self) -> StubUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class StubChunker:
    def split(self, document: str) -> list[str]:
        assert document == "document body"
        return ["first chunk", "second chunk"]


class StubEmbedder:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(index)] * 1024 for index, _ in enumerate(texts)]


def make_uow_factory(context: str | None, chunks: StubChunks) -> Callable[[], WorkerUnitOfWork]:
    def factory() -> WorkerUnitOfWork:
        return cast(WorkerUnitOfWork, StubUnitOfWork(context, chunks))

    return factory


@pytest.mark.asyncio
async def test_service_embeds_and_replaces_document_chunks() -> None:
    chunks = StubChunks()
    service = DocumentProcessingService(
        make_uow_factory("document body", chunks),
        cast(Any, StubChunker()),
        StubEmbedder(),
    )

    chunk_count = await service.process(42)

    assert chunk_count == 2
    assert chunks.replaced is not None
    assert chunks.replaced[0:2] == (42, ["first chunk", "second chunk"])
    assert all(len(embedding) == 1024 for embedding in chunks.replaced[2])


@pytest.mark.asyncio
async def test_service_skips_missing_document() -> None:
    chunks = StubChunks()
    service = DocumentProcessingService(
        make_uow_factory(None, chunks),
        cast(Any, StubChunker()),
        StubEmbedder(),
    )

    assert await service.process(404) is None
    assert chunks.replaced is None
