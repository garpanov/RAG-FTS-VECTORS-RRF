import asyncio
import logging

import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError

from app.messaging import DocumentChunkingTask
from worker.config import get_worker_settings

logger = logging.getLogger(__name__)


async def handle_document_task(task: DocumentChunkingTask) -> None:
    logger.info("Received document chunking task for document_id=%d", task.document_id)


async def consume_message(message: AbstractIncomingMessage) -> None:
    async with message.process(requeue=False):
        try:
            task = DocumentChunkingTask.model_validate_json(message.body)
        except ValidationError:
            logger.exception("Discarding invalid document chunking task")
            return

        await handle_document_task(task)


async def run() -> None:
    settings = get_worker_settings()
    connection = await aio_pika.connect_robust(str(settings.rabbitmq_url))

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue(settings.document_chunking_queue, durable=True)
        logger.info("Waiting for document chunking tasks")
        await queue.consume(consume_message)
        await asyncio.Future()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
