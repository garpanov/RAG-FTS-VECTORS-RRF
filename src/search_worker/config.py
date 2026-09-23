from functools import lru_cache

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class SearchWorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: PostgresDsn
    grpc_host: str = "0.0.0.0"
    grpc_port: int = Field(default=50051, ge=1, le=65535)
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=8, gt=0)


@lru_cache
def get_search_worker_settings() -> SearchWorkerSettings:
    return SearchWorkerSettings()  # type: ignore[call-arg]
