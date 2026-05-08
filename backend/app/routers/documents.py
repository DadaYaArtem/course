from fastapi import APIRouter, Depends, File, UploadFile

from app.schemas.documents import DocumentSource, DocumentUploadResponse
from app.services.document_service import (
    DocumentService,
    get_document_service,
)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentUploadResponse:
    """Upload a PDF document and trigger document processing."""
    return await service.upload_document(file)


@router.get("", response_model=list[DocumentSource])
async def list_documents(
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentSource]:
    """List document sources currently indexed in Neo4j."""
    return await service.list_documents()
