from typing import Protocol

from app.messaging import DocumentTaskPublisher
from app.models import Document
from app.repositories import DocumentNumberConflictError
from app.search_client import SearchChunk
from app.unit_of_work import UnitOfWork


class DocumentAlreadyExistsError(Exception):
    """Raised when a document with the requested number already exists."""


class DocumentService:
    def __init__(
        self,
        unit_of_work: UnitOfWork,
        task_publisher: DocumentTaskPublisher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._task_publisher = task_publisher

    async def create_document(self, document_number: str, context: str) -> Document:
        try:
            async with self._unit_of_work:
                document = await self._unit_of_work.documents.create(document_number, context)
        except DocumentNumberConflictError as error:
            raise DocumentAlreadyExistsError(document_number) from error

        await self._task_publisher.publish_document_created(document.id)
        return document


class SearchClient(Protocol):
    async def search(self, question: str) -> list[SearchChunk]: ...


class SearchService:
    def __init__(self, client: SearchClient) -> None:
        self._client = client

    async def search(self, question: str) -> list[SearchChunk]:
        return await self._client.search(question)
