from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document


class DocumentNumberConflictError(Exception):
    """Raised when a document number violates its unique constraint."""


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document_number: str, context: str) -> Document:
        document = Document(document_number=document_number, context=context)
        self._session.add(document)

        try:
            await self._session.flush()
        except IntegrityError as error:
            if isinstance(error.orig, UniqueViolation):
                raise DocumentNumberConflictError from error
            raise

        await self._session.refresh(document)
        return document
