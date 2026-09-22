from typing import Protocol

import aio_pika
from aio_pika.abc import AbstractRobustConnection
from pydantic import BaseModel, PositiveInt

DOCUMENT_CHUNKING_QUEUE = "document.chunking"


class DocumentChunkingTask(BaseModel):
    document_id: PositiveInt


class DocumentTaskPublisher(Protocol):
    async def publish_document_created(self, document_id: int) -> None: ...


class RabbitMQDocumentTaskPublisher:
    def __init__(self, rabbitmq_url: str, queue_name: str) -> None:
        self._rabbitmq_url = rabbitmq_url
        self._queue_name = queue_name
        self._connection: AbstractRobustConnection | None = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self._rabbitmq_url)

    async def close(self) -> None:
        if self._connection is not None:
            await self._connection.close()
            self._connection = None

    async def publish_document_created(self, document_id: int) -> None:
        if self._connection is None:
            raise RuntimeError("RabbitMQ publisher is not connected")

        channel = await self._connection.channel()
        try:
            await channel.declare_queue(self._queue_name, durable=True)
            task = DocumentChunkingTask(document_id=document_id)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=task.model_dump_json().encode(),
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key=self._queue_name,
            )
        finally:
            await channel.close()
