import asyncio
import logging

from grpc import aio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from contracts import search_pb2_grpc
from search_worker.config import get_search_worker_settings
from search_worker.grpc_service import ChunkSearchGrpcService
from search_worker.services import ChunkSearchService
from search_worker.unit_of_work import SearchUnitOfWork
from worker.embeddings import QwenEmbeddingModel

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_search_worker_settings()
    engine = create_async_engine(str(settings.database_url), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedding_model = await asyncio.to_thread(
        QwenEmbeddingModel,
        settings.embedding_model,
        settings.embedding_device,
        settings.embedding_batch_size,
    )
    service = ChunkSearchService(
        lambda: SearchUnitOfWork(session_factory()),
        embedding_model,
    )
    server = aio.server()
    search_pb2_grpc.add_ChunkSearchServicer_to_server(  # type: ignore[no-untyped-call]
        ChunkSearchGrpcService(service),
        server,
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)

    try:
        await server.start()
        logger.info("Search worker is listening on %s", address)
        await server.wait_for_termination()
    finally:
        await server.stop(grace=5)
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
