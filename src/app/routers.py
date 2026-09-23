from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_document_service, get_search_service
from app.schemas import (
    ChunkResponse,
    DocumentCreate,
    DocumentResponse,
    SearchRequest,
    SearchResponse,
)
from app.search_client import SearchWorkerUnavailableError
from app.services import DocumentAlreadyExistsError, DocumentService, SearchService

documents_router = APIRouter(prefix="/documents", tags=["documents"])
search_router = APIRouter(prefix="/search", tags=["search"])
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]
SearchServiceDependency = Annotated[SearchService, Depends(get_search_service)]


@documents_router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    payload: DocumentCreate,
    service: DocumentServiceDependency,
) -> DocumentResponse:
    try:
        document = await service.create_document(payload.document_number, payload.context)
    except DocumentAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A document with this document number already exists",
        ) from error

    return DocumentResponse.model_validate(document)


@search_router.post("", response_model=SearchResponse)
async def search_chunks(
    payload: SearchRequest,
    service: SearchServiceDependency,
) -> SearchResponse:
    try:
        chunks = await service.search(payload.question)
    except SearchWorkerUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search worker is unavailable",
        ) from error

    return SearchResponse(
        chunks=[
            ChunkResponse(
                document_id=chunk.document_id,
                document_number=chunk.document_number,
                chunk_number=chunk.chunk_number,
                content=chunk.content,
                distance=chunk.distance,
            )
            for chunk in chunks
        ]
    )
