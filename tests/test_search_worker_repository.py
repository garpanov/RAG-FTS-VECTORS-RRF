from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from search_worker.repositories import ChunkSearchRepository


@pytest.mark.asyncio
async def test_repository_returns_nearest_chunk_rows() -> None:
    result = Mock()
    result.all.return_value = [
        SimpleNamespace(
            document_id=42,
            document_number="001-A",
            chunk_number=2,
            content="closest chunk",
            distance=0.125,
        )
    ]
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=result)
    repository = ChunkSearchRepository(session)

    matches = await repository.find_nearest([0.5] * 1024, 30)

    assert len(matches) == 1
    assert matches[0].document_number == "001-A"
    assert matches[0].distance == 0.125
    statement = session.execute.await_args.args[0]
    assert "chunks.embedding <=>" in str(statement)
    assert "ORDER BY distance" in str(statement)


@pytest.mark.asyncio
async def test_repository_returns_ranked_fts_chunk_rows() -> None:
    result = Mock()
    result.all.return_value = [
        SimpleNamespace(
            document_id=42,
            document_number="001-A",
            chunk_number=2,
            content="matching chunk",
            rank=0.75,
        )
    ]
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock(return_value=result)
    repository = ChunkSearchRepository(session)

    matches = await repository.find_fts("matching words", 30)

    assert len(matches) == 1
    assert matches[0].document_number == "001-A"
    assert matches[0].rank == 0.75
    statement = session.execute.await_args.args[0]
    statement_sql = str(statement)
    assert "websearch_to_tsquery" in statement_sql
    assert "chunks.search_vector @@" in statement_sql
    assert "ORDER BY rank DESC" in statement_sql
    assert statement._limit_clause.value == 30
