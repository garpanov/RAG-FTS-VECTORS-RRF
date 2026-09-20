from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.unit_of_work import UnitOfWork


@pytest.mark.asyncio
async def test_unit_of_work_commits_successful_operation() -> None:
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async with UnitOfWork(session):
        pass

    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_failed_operation() -> None:
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    with pytest.raises(RuntimeError, match="operation failed"):
        async with UnitOfWork(session):
            raise RuntimeError("operation failed")

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_commit_failure() -> None:
    commit_error = RuntimeError("commit failed")
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock(side_effect=commit_error)
    session.rollback = AsyncMock()

    with pytest.raises(RuntimeError, match="commit failed"):
        async with UnitOfWork(session):
            pass

    session.rollback.assert_awaited_once_with()
