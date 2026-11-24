from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.core.exceptions import DocumentServiceError
from app.repositories.document_jobs import DocumentJobRepository, get_document_job_repository
from app.schemas.document_jobs import DocumentJob
from app.services.document_service import save_upload

router = APIRouter(prefix="/document-jobs", tags=["document jobs"])


def require_parser() -> None:
    if not settings.document_parser_enabled:
        raise HTTPException(503, "Document processing is disabled.")


def store_job(repository: DocumentJobRepository, filename: str, content: bytes) -> DocumentJob:
    path = save_upload(Path(settings.document_upload_dir).resolve(), filename, content)
    try:
        return repository.create(filename, path, settings.document_job_max_attempts)
    except Exception:
        path.unlink(missing_ok=True)
        raise


@router.post("", status_code=202, response_model=DocumentJob)
async def create_job(
    response: Response,
    file: UploadFile = File(...),
    repository: DocumentJobRepository = Depends(get_document_job_repository),
) -> DocumentJob:
    require_parser()
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf") or len(filename) > 200:
        raise DocumentServiceError("Upload a PDF with a filename of at most 200 characters.")
    content = await file.read(settings.document_job_max_bytes + 1)
    if len(content) > settings.document_job_max_bytes:
        raise HTTPException(413, "PDF exceeds the configured size limit.")
    if b"%PDF-" not in content[:1024]:
        raise DocumentServiceError("File does not contain a PDF header.")
    job = await run_in_threadpool(store_job, repository, filename, content)
    response.headers["Location"] = f"/document-jobs/{job.id}"
    return job


@router.get("/{job_id}", response_model=DocumentJob)
def get_job(
    job_id: UUID,
    repository: DocumentJobRepository = Depends(get_document_job_repository),
) -> DocumentJob:
    job = repository.get(str(job_id))
    if job is None:
        raise HTTPException(404, "Document job not found.")
    return job


@router.post("/{job_id}/retry", status_code=202, response_model=DocumentJob)
def retry_job(
    job_id: UUID,
    repository: DocumentJobRepository = Depends(get_document_job_repository),
) -> DocumentJob:
    require_parser()
    get_job(job_id, repository)
    job = repository.retry(str(job_id))
    if job is None:
        raise HTTPException(409, "Only failed jobs with attempts remaining can be retried.")
    return job
