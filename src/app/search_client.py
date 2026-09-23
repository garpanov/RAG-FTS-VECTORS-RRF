from dataclasses import dataclass
from typing import cast

import grpc
from grpc import aio

from contracts import search_pb2, search_pb2_grpc


class SearchWorkerUnavailableError(Exception):
    """Raised when the search worker cannot serve a request."""


@dataclass(frozen=True, slots=True)
class SearchChunk:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float


@dataclass(frozen=True, slots=True)
class RerankedSearchChunk:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float
    reranker_score: float


class GrpcSearchWorkerClient:
    def __init__(self, target: str) -> None:
        self._channel = aio.insecure_channel(target)
        self._stub = search_pb2_grpc.ChunkSearchStub(self._channel)  # type: ignore[no-untyped-call]

    async def search(self, question: str) -> list[SearchChunk]:
        request = search_pb2.SearchChunksRequest(question=question, limit=30)
        try:
            response = await self._stub.SearchChunks(request)
        except grpc.aio.AioRpcError as error:
            raise SearchWorkerUnavailableError from error

        return [
            SearchChunk(
                document_id=chunk.document_id,
                document_number=chunk.document_number,
                chunk_number=chunk.chunk_number,
                content=chunk.content,
                distance=chunk.distance,
            )
            for chunk in cast(search_pb2.SearchChunksResponse, response).chunks
        ]

    async def rerank(self, question: str) -> list[RerankedSearchChunk]:
        request = search_pb2.RerankChunksRequest(question=question)
        try:
            response = await self._stub.RerankChunks(request)
        except grpc.aio.AioRpcError as error:
            raise SearchWorkerUnavailableError from error

        return [
            RerankedSearchChunk(
                document_id=chunk.document_id,
                document_number=chunk.document_number,
                chunk_number=chunk.chunk_number,
                content=chunk.content,
                distance=chunk.distance,
                reranker_score=chunk.reranker_score,
            )
            for chunk in cast(search_pb2.RerankChunksResponse, response).chunks
        ]

    async def close(self) -> None:
        await self._channel.close()
