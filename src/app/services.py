from app.models import Document
from app.repositories import DocumentNumberConflictError
from app.unit_of_work import UnitOfWork


class DocumentAlreadyExistsError(Exception):
    """Raised when a document with the requested number already exists."""


class DocumentService:
    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def create_document(self, document_number: str, context: str) -> Document:
        try:
            async with self._unit_of_work:
                return await self._unit_of_work.documents.create(document_number, context)
        except DocumentNumberConflictError as error:
            raise DocumentAlreadyExistsError(document_number) from error
