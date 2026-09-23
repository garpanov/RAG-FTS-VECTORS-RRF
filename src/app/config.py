from functools import lru_cache

from pydantic import AmqpDsn, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.messaging import DOCUMENT_CHUNKING_QUEUE


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: PostgresDsn
    rabbitmq_url: AmqpDsn
    document_chunking_queue: str = DOCUMENT_CHUNKING_QUEUE
    search_worker_target: str = "localhost:50051"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
