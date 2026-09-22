from functools import lru_cache

from pydantic import AmqpDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.messaging import DOCUMENT_CHUNKING_QUEUE


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rabbitmq_url: AmqpDsn = AmqpDsn("amqp://guest:guest@localhost:5672/")
    document_chunking_queue: str = DOCUMENT_CHUNKING_QUEUE


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()
