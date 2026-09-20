from app.models import Document
from app.repositories import DocumentNumberConflictError, DocumentRepository


class DocumentAlreadyExistsError(Exception):
    """Raised when a document with the requested number already exists."""


class DocumentService:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def create_document(self, document_number: str, context: str) -> Document:
        try:
            return await self._repository.create(document_number, context)
        except DocumentNumberConflictError as error:
            raise DocumentAlreadyExistsError(document_number) from error
