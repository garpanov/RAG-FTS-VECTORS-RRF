from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class DocumentCreate(BaseModel):
    document_number: str
    context: str

    @field_validator("document_number", mode="before")
    @classmethod
    def normalize_document_number(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("document_number", "context")
    @classmethod
    def reject_blank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_number: str
    context: str
    created_at: datetime


class SearchRequest(BaseModel):
    question: str

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("must not be blank")
        return question


class ChunkResponse(BaseModel):
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float


class SearchResponse(BaseModel):
    chunks: list[ChunkResponse]


class RerankedChunkResponse(ChunkResponse):
    reranker_score: float


class RerankerResponse(BaseModel):
    chunks: list[RerankedChunkResponse]
