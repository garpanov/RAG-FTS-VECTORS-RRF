from types import TracebackType
from typing import Literal, cast

import pytest

from app.models import Document
from app.repositories import DocumentNumberConflictError
from app.services import DocumentAlreadyExistsError, DocumentService
from app.unit_of_work import UnitOfWork


class StubDocumentRepository:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.duplicate = duplicate

    async def create(self, document_number: str, context: str) -> Document:
        if self.duplicate:
            raise DocumentNumberConflictError
        return Document(id=42, document_number=document_number, context=context)


class StubTaskPublisher:
    def __init__(self) -> None:
        self.document_ids: list[int] = []

    async def publish_document_created(self, document_id: int) -> None:
        self.document_ids.append(document_id)


class StubUnitOfWork:
    def __init__(self, *, duplicate: bool = False) -> None:
        self.documents = StubDocumentRepository(duplicate=duplicate)
        self.entered = False
        self.received_exception: type[BaseException] | None = None

    async def __aenter__(self) -> StubUnitOfWork:
        self.entered = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self.received_exception = exc_type
        return False


@pytest.mark.asyncio
async def test_service_creates_document_inside_unit_of_work() -> None:
    unit_of_work = StubUnitOfWork()
    publisher = StubTaskPublisher()
    service = DocumentService(cast(UnitOfWork, unit_of_work), publisher)

    document = await service.create_document("001-A", "context")

    assert unit_of_work.entered
    assert unit_of_work.received_exception is None
    assert document.document_number == "001-A"
    assert publisher.document_ids == [42]


@pytest.mark.asyncio
async def test_service_maps_repository_conflict_after_transaction_rollback() -> None:
    unit_of_work = StubUnitOfWork(duplicate=True)
    publisher = StubTaskPublisher()
    service = DocumentService(cast(UnitOfWork, unit_of_work), publisher)

    with pytest.raises(DocumentAlreadyExistsError):
        await service.create_document("001-A", "context")

    assert unit_of_work.received_exception is DocumentNumberConflictError
    assert publisher.document_ids == []
