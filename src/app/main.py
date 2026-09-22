from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.messaging import RabbitMQDocumentTaskPublisher
from app.routers import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    publisher = RabbitMQDocumentTaskPublisher(
        str(settings.rabbitmq_url),
        settings.document_chunking_queue,
    )
    await publisher.connect()
    app.state.document_task_publisher = publisher
    try:
        yield
    finally:
        await publisher.close()


app = FastAPI(title="Document ingestion service", lifespan=lifespan)
app.include_router(documents_router)
