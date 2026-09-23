from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession

from search_worker.repositories import ChunkSearchRepository


class SearchUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.chunks = ChunkSearchRepository(session)

    async def __aenter__(self) -> SearchUnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if exc_type is not None:
                await self._session.rollback()
        finally:
            await self._session.close()
