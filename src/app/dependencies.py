from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services import DocumentService
from app.unit_of_work import UnitOfWork

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_document_service(session: SessionDependency) -> DocumentService:
    return DocumentService(UnitOfWork(session))
