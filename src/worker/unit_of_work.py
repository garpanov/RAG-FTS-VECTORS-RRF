from types import TracebackType
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from worker.repositories import ChunkRepository, WorkerDocumentRepository


class WorkerUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.documents = WorkerDocumentRepository(session)
        self.chunks = ChunkRepository(session)

    async def __aenter__(self) -> WorkerUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None:
            try:
                await self._session.rollback()
            finally:
                await self._session.close()
            return False

        try:
            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise
        finally:
            await self._session.close()

        return False
