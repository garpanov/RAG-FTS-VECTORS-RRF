from dataclasses import dataclass
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document


@dataclass(frozen=True, slots=True)
class ChunkMatch:
    document_id: int
    document_number: str
    chunk_number: int
    content: str
    distance: float


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
