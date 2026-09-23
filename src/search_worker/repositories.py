from dataclasses import dataclass
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document


@dataclass(frozen=True, slots=True)
class ChunkMatch:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float


@dataclass(frozen=True, slots=True)
class FtsChunkMatch:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    rank: float


class ChunkSearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_nearest(
        self,
        embedding: list[float],
        limit: int,
    ) -> list[ChunkMatch]:
        distance = Chunk.embedding.cosine_distance(embedding).label("distance")
        statement = (
            select(
                Chunk.document_id,
                Document.document_number,
                Chunk.chunk_number,
                Chunk.content,
                distance,
            )
            .join(Document, Document.id == Chunk.document_id)
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            ChunkMatch(
                document_id=row.document_id,
                document_number=row.document_number,
                chunk_number=row.chunk_number,
                content=row.content,
                distance=cast(float, row.distance),
            )
            for row in rows
        ]

    async def find_fts(self, question: str, limit: int) -> list[FtsChunkMatch]:
        query = func.websearch_to_tsquery("simple", question)
        rank = func.ts_rank_cd(Chunk.search_vector, query).label("rank")
        statement = (
            select(
                Chunk.document_id,
                Document.document_number,
                Chunk.chunk_number,
                Chunk.content,
                rank,
            )
            .join(Document, Document.id == Chunk.document_id)
            .where(Chunk.search_vector.op("@@")(query))
            .order_by(rank.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        return [
            FtsChunkMatch(
                document_id=row.document_id,
                document_number=row.document_number,
                chunk_number=row.chunk_number,
                content=row.content,
                rank=cast(float, row.rank),
            )
            for row in rows
        ]
