from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.messaging import RabbitMQDocumentTaskPublisher
from app.routers import documents_router, search_router
from app.search_client import GrpcSearchWorkerClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    publisher = RabbitMQDocumentTaskPublisher(
        str(settings.rabbitmq_url),
        settings.document_chunking_queue,
    )
    await publisher.connect()
    search_worker_client = GrpcSearchWorkerClient(settings.search_worker_target)
    app.state.document_task_publisher = publisher
    app.state.search_worker_client = search_worker_client
    try:
        yield
    finally:
        await search_worker_client.close()
        await publisher.close()


app = FastAPI(title="Document ingestion service", lifespan=lifespan)
app.include_router(documents_router)
app.include_router(search_router)
