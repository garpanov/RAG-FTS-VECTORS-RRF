from collections.abc import Sequence

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document


class WorkerDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, document_id: int) -> Document | None:
        return await self._session.get(Document, document_id)


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace(
        self,
        document_id: int,
        contents: Sequence[str],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if len(contents) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding")

        await self._session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        self._session.add_all(
            [
                Chunk(
                    document_id=document_id,
                    chunk_number=chunk_number,
                    content=content,
                    embedding=list(embedding),
                )
                for chunk_number, (content, embedding) in enumerate(
                    zip(contents, embeddings, strict=True)
                )
            ]
        )
