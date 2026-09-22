from functools import lru_cache

from pydantic import AmqpDsn, Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.messaging import DOCUMENT_CHUNKING_QUEUE


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    rabbitmq_url: AmqpDsn
    database_url: PostgresDsn
    document_chunking_queue: str = DOCUMENT_CHUNKING_QUEUE
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=8, gt=0)
    chunk_max_tokens: int = Field(default=300, gt=0)
    chunk_overlap_tokens: int = Field(default=30, ge=0)


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()  # type: ignore[call-arg]
