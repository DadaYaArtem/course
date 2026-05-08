from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.core.exceptions import DocumentServiceError, LLMError
from app.main import app
from app.schemas.documents import DocumentSource, DocumentUploadResponse
from app.schemas.query import QueryServiceResult, QueryType
from app.services.document_service import get_document_service
from app.services.query_service import get_query_service


class FakeQueryService:
    """Query service test double for API tests."""

    async def answer(self, text: str) -> QueryServiceResult:
        """Return a fake query answer."""
        return QueryServiceResult(
            answer=f"Answer for: {text}",
            query_type=QueryType.DEFINITION,
            source_entities=["BERT"],
            from_kb=True,
        )


class FakeDocumentService:
    """Document service test double for API tests."""

    async def upload_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Return a fake upload response."""
        return DocumentUploadResponse(
            filename=file.filename or "document.pdf",
            saved_path="uploads/documents/test.pdf",
            status="uploaded",
            indexed=False,
            message="Document saved; parser pipeline is disabled.",
        )

    async def list_documents(self) -> list[DocumentSource]:
        """Return fake indexed document sources."""
        return [
            DocumentSource(source="manual_seed"),
            DocumentSource(source="sample.pdf"),
        ]


class FailingQueryService:
    """Query service test double that raises an LLM error."""

    async def answer(self, text: str) -> QueryServiceResult:
        """Raise an LLM error."""
        raise LLMError("LLM is unavailable.")


class FailingDocumentService:
    """Document service test double that raises a document error."""

    async def upload_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Raise a document error."""
        raise DocumentServiceError("Only PDF uploads are supported.")

    async def list_documents(self) -> list[DocumentSource]:
        """Return no documents."""
        return []


def override_query_service() -> FakeQueryService:
    """Return fake query service dependency."""
    return FakeQueryService()


def override_document_service() -> FakeDocumentService:
    """Return fake document service dependency."""
    return FakeDocumentService()


def override_failing_query_service() -> FailingQueryService:
    """Return failing query service dependency."""
    return FailingQueryService()


def override_failing_document_service() -> FailingDocumentService:
    """Return failing document service dependency."""
    return FailingDocumentService()


def test_health_endpoint() -> None:
    """Health endpoint returns liveness status."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_endpoint() -> None:
    """POST /query returns the query service result."""
    app.dependency_overrides[get_query_service] = override_query_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/query",
                json={"text": "What is BERT?", "language": "en"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Answer for: What is BERT?",
        "query_type": "definition",
        "source_entities": ["BERT"],
        "from_kb": True,
    }


def test_documents_upload_endpoint() -> None:
    """POST /documents/upload returns document upload status."""
    app.dependency_overrides[get_document_service] = override_document_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                files={"file": ("sample.pdf", b"%PDF-1.4", "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "sample.pdf"
    assert body["status"] == "uploaded"
    assert body["indexed"] is False


def test_documents_list_endpoint() -> None:
    """GET /documents returns indexed sources."""
    app.dependency_overrides[get_document_service] = override_document_service
    try:
        with TestClient(app) as client:
            response = client.get("/documents")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == [
        {"source": "manual_seed"},
        {"source": "sample.pdf"},
    ]


def test_validation_error_returns_problem_details() -> None:
    """Request validation errors use RFC 7807 Problem Details."""
    app.dependency_overrides[get_query_service] = override_query_service
    try:
        with TestClient(app) as client:
            response = client.post("/query", json={"language": "en"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "Validation Error"
    assert body["status"] == 422
    assert body["instance"] == "/query"
    assert "errors" in body


def test_app_error_returns_problem_details() -> None:
    """Application errors use RFC 7807 Problem Details."""
    app.dependency_overrides[get_query_service] = override_failing_query_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/query",
                json={"text": "What is BERT?", "language": "en"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "LLM Error"
    assert body["detail"] == "LLM is unavailable."
    assert body["instance"] == "/query"


def test_document_error_returns_problem_details() -> None:
    """Document service errors use RFC 7807 Problem Details."""
    app.dependency_overrides[get_document_service] = override_failing_document_service
    try:
        with TestClient(app) as client:
            response = client.post(
                "/documents/upload",
                files={"file": ("sample.txt", b"text", "text/plain")},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["title"] == "Document Error"
    assert body["detail"] == "Only PDF uploads are supported."
    assert body["instance"] == "/documents/upload"
