from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    """Response returned after a document upload request."""

    filename: str
    saved_path: str
    status: str
    indexed: bool
    message: str


class DocumentSource(BaseModel):
    """Single indexed document source."""

    source: str
