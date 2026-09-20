from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_document_service
from app.schemas import DocumentCreate, DocumentResponse
from app.services import DocumentAlreadyExistsError, DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
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
