import grpc
from grpc import aio

from contracts import search_pb2, search_pb2_grpc
from search_worker.services import ChunkSearchService


class ChunkSearchGrpcService(search_pb2_grpc.ChunkSearchServicer):
    def __init__(self, service: ChunkSearchService) -> None:
        self._service = service

    async def SearchChunks(
        self,
        request: search_pb2.SearchChunksRequest,
        context: aio.ServicerContext[
            search_pb2.SearchChunksRequest,
            search_pb2.SearchChunksResponse,
        ],
    ) -> search_pb2.SearchChunksResponse:
        question = request.question.strip()
        if not question:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "question must not be blank")

        matches = await self._service.search(question, request.limit or 30)
        return search_pb2.SearchChunksResponse(
            chunks=[
                search_pb2.Chunk(
                    document_id=match.document_id,
                    document_number=match.document_number,
                    chunk_number=match.chunk_number,
                    content=match.content,
                    distance=match.distance,
                )
                for match in matches
            ]
        )

    async def RerankChunks(
        self,
        request: search_pb2.RerankChunksRequest,
        context: aio.ServicerContext[
            search_pb2.RerankChunksRequest,
            search_pb2.RerankChunksResponse,
        ],
    ) -> search_pb2.RerankChunksResponse:
        question = request.question.strip()
        if not question:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, "question must not be blank")

        matches = await self._service.rerank(question)
        return search_pb2.RerankChunksResponse(
            chunks=[
                search_pb2.RerankedChunk(
                    document_id=match.document_id,
                    document_number=match.document_number,
                    chunk_number=match.chunk_number,
                    content=match.content,
                    distance=match.distance,
                    reranker_score=match.reranker_score,
                )
                for match in matches
            ]
        )
