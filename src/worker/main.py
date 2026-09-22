import asyncio
import logging
from functools import partial

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.messaging import DocumentChunkingTask
from worker.chunking import MarkdownChunker
from worker.config import get_worker_settings
from worker.embeddings import QwenEmbeddingModel
from worker.services import DocumentProcessingService
from worker.unit_of_work import WorkerUnitOfWork

logger = logging.getLogger(__name__)


async def consume_message(
    message: AbstractIncomingMessage,
    service: DocumentProcessingService,
) -> None:
    try:
        task = DocumentChunkingTask.model_validate_json(message.body)
    except ValidationError:
        logger.exception("Discarding invalid document chunking task")
        await message.reject(requeue=False)
        return

    async with message.process(requeue=True):
        chunk_count = await service.process(task.document_id)
        if chunk_count is None:
            logger.warning("Document id=%d does not exist; skipping task", task.document_id)
            return
        logger.info("Stored %d chunks for document id=%d", chunk_count, task.document_id)


async def run() -> None:
    settings = get_worker_settings()
    if settings.chunk_overlap_tokens >= settings.chunk_max_tokens:
        raise ValueError("CHUNK_OVERLAP_TOKENS must be less than CHUNK_MAX_TOKENS")

    engine = create_async_engine(str(settings.database_url), pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    embedding_model = await asyncio.to_thread(
        QwenEmbeddingModel,
        settings.embedding_model,
        settings.embedding_device,
        settings.embedding_batch_size,
    )
    chunker = MarkdownChunker(
        embedding_model,
        max_tokens=settings.chunk_max_tokens,
        overlap_tokens=settings.chunk_overlap_tokens,
    )
    service = DocumentProcessingService(
        lambda: WorkerUnitOfWork(session_factory()),
        chunker,
        embedding_model,
    )
    connection = await aio_pika.connect_robust(str(settings.rabbitmq_url))

    try:
        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue(settings.document_chunking_queue, durable=True)
            logger.info("Waiting for document chunking tasks")
            await queue.consume(partial(consume_message, service=service))
            await asyncio.Future()
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
