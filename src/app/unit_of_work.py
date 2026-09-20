from types import TracebackType
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import DocumentRepository


class UnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.documents = DocumentRepository(session)

    async def __aenter__(self) -> UnitOfWork:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None:
            await self._session.rollback()
            return False

        try:
            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return False
