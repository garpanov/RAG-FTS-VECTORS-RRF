from unittest.mock import AsyncMock, Mock

import pytest
from psycopg.errors import NotNullViolation, UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Document
from app.repositories import DocumentNumberConflictError, DocumentRepository


@pytest.mark.asyncio
async def test_repository_flushes_and_refreshes_document() -> None:
    session = Mock(spec=AsyncSession)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    repository = DocumentRepository(session)

    document = await repository.create("001-A", "context")

    assert isinstance(document, Document)
    assert document.document_number == "001-A"
    assert document.context == "context"
    session.add.assert_called_once_with(document)
    session.flush.assert_awaited_once_with()
    session.refresh.assert_awaited_once_with(document)


@pytest.mark.asyncio
async def test_repository_reports_unique_constraint_conflict() -> None:
    session = Mock(spec=AsyncSession)
    session.flush = AsyncMock(side_effect=IntegrityError("statement", {}, UniqueViolation()))
    session.refresh = AsyncMock()
    repository = DocumentRepository(session)

    with pytest.raises(DocumentNumberConflictError):
        await repository.create("001-A", "context")

    session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_repository_does_not_misreport_other_integrity_errors() -> None:
    error = IntegrityError("statement", {}, NotNullViolation())
    session = Mock(spec=AsyncSession)
    session.flush = AsyncMock(side_effect=error)
    session.refresh = AsyncMock()
    repository = DocumentRepository(session)

    with pytest.raises(IntegrityError) as raised:
        await repository.create("001-A", "context")

    assert raised.value is error
