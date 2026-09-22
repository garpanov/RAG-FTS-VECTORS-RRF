from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.messaging import DocumentTaskPublisher
from app.services import DocumentService
from app.unit_of_work import UnitOfWork

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_task_publisher(request: Request) -> DocumentTaskPublisher:
    return cast(DocumentTaskPublisher, request.app.state.document_task_publisher)


TaskPublisherDependency = Annotated[DocumentTaskPublisher, Depends(get_task_publisher)]


def get_document_service(
    session: SessionDependency,
    task_publisher: TaskPublisherDependency,
) -> DocumentService:
    return DocumentService(UnitOfWork(session), task_publisher)
