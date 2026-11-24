import os
import re
import sys
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from fastapi import Depends, UploadFile

from app.core.config import settings
from app.core.exceptions import DocumentServiceError
from app.repositories.graph_repository import GraphRepository, get_graph_repository
from app.schemas.documents import DocumentSource, DocumentUploadResponse


class ParserPipelineProtocol(Protocol):
    """Protocol for document parser pipeline runners."""

    async def run(self, input_path: Path) -> tuple[bool, str]:
        """Run parser pipeline for an uploaded document."""


class LocalParserPipeline:
    """Run the local parser pipeline as a subprocess when enabled."""

    async def run(self, input_path: Path, *, timeout: int | None = None) -> tuple[bool, str]:
        """Run parser CLI for an uploaded document.

        Args:
            input_path: Saved PDF path.

        Returns:
            Whether indexing was triggered and a status message.
        """
        if not settings.document_parser_enabled:
            return False, "Document saved; parser pipeline is disabled."

        import asyncio

        parser_dir = Path(settings.parser_service_dir).resolve()
        if not parser_dir.exists():
            raise DocumentServiceError(f"Parser service directory not found: {parser_dir}")

        subprocess_env = {
            **os.environ,
            "NEO4J_URI": settings.neo4j_uri,
            "NEO4J_USER": settings.neo4j_user,
            "NEO4J_PASSWORD": settings.neo4j_password,
            "NEO4J_DATABASE": settings.neo4j_database,
        }

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "parser.main",
            "--input",
            str(input_path),
            "--output-dir",
            settings.parser_output_dir,
            "--import-neo4j",
            cwd=parser_dir,
            env=subprocess_env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        communication = asyncio.create_task(process.communicate())
        try:
            stdout, stderr = await asyncio.wait_for(asyncio.shield(communication), timeout)
        except (TimeoutError, asyncio.CancelledError):
            if process.returncode is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            await communication
            raise
        if process.returncode != 0:
            detail = stderr.decode("utf-8", errors="replace").strip()
            raise DocumentServiceError(f"Parser pipeline failed: {detail}")

        message = stdout.decode("utf-8", errors="replace").strip()
        return True, message or "Document parsed and imported to Neo4j."


class DocumentService:
    """Handle document uploads and indexed source listing."""

    def __init__(
        self,
        repository: GraphRepository,
        parser_pipeline: ParserPipelineProtocol | None = None,
        upload_dir: str | None = None,
    ) -> None:
        """Initialize document service.

        Args:
            repository: Graph repository used for indexed source listing.
            parser_pipeline: Optional parser runner dependency.
            upload_dir: Optional directory for uploaded documents.
        """
        self._repository = repository
        self._parser_pipeline = parser_pipeline or LocalParserPipeline()
        self._upload_dir = Path(upload_dir or settings.document_upload_dir)

    async def upload_document(self, file: UploadFile) -> DocumentUploadResponse:
        """Save an uploaded PDF and trigger the parser pipeline.

        Args:
            file: Uploaded PDF file.

        Returns:
            Upload and parser status.
        """
        original_name = file.filename or "document.pdf"
        if not original_name.lower().endswith(".pdf"):
            raise DocumentServiceError("Only PDF uploads are supported.")

        content = await file.read()
        if not content:
            raise DocumentServiceError("Uploaded file is empty.")

        saved_path = self._save_upload(original_name, content)
        indexed, message = await self._parser_pipeline.run(saved_path)
        return DocumentUploadResponse(
            filename=original_name,
            saved_path=str(saved_path),
            status="indexed" if indexed else "uploaded",
            indexed=indexed,
            message=message,
        )

    async def list_documents(self) -> list[DocumentSource]:
        """List document sources indexed in Neo4j."""
        sources = await self._repository.list_sources()
        return [DocumentSource(source=item["source"]) for item in sources]

    def _save_upload(self, original_name: str, content: bytes) -> Path:
        """Persist uploaded file content to the upload directory."""
        return save_upload(self._upload_dir, original_name, content)


def save_upload(directory: Path, original_name: str, content: bytes) -> Path:
    """Save a document under a unique, filesystem-safe name."""
    directory.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original_name).name)
    saved_path = directory / f"{uuid4().hex}_{safe_name}"
    try:
        saved_path.write_bytes(content)
    except OSError:
        saved_path.unlink(missing_ok=True)
        raise
    return saved_path


async def get_document_service(
    repository: GraphRepository = Depends(get_graph_repository),
) -> DocumentService:
    """FastAPI dependency that injects DocumentService."""
    return DocumentService(repository=repository)
