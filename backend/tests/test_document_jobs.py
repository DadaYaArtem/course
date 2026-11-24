from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

from app import main
from app.core.config import settings
from app.document_worker import process_next
from app.repositories.document_jobs import DocumentJobRepository, get_document_job_repository


@pytest.fixture
def job_api(tmp_path, monkeypatch):
    repository = DocumentJobRepository(tmp_path / "jobs.sqlite3")
    monkeypatch.setattr(settings, "document_upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "document_parser_enabled", True)
    monkeypatch.setattr(settings, "document_job_max_attempts", 2)
    monkeypatch.setitem(
        main.app.dependency_overrides, get_document_job_repository, lambda: repository
    )
    with TestClient(main.app) as client:
        yield client, repository


def submit_pdf(client):
    return client.post("/document-jobs", files={"file": ("sample.pdf", b"%PDF-1.4")})


@pytest.mark.asyncio
async def test_pdf_is_accepted_before_worker_runs(job_api):
    client, repository = job_api
    response = submit_pdf(client)
    assert response.status_code == 202
    location = response.headers["location"]
    assert client.get(location).json()["status"] == "queued"
    assert "path" not in response.json()

    class Parser:
        async def run(self, path, *, timeout):
            assert path.read_bytes() == b"%PDF-1.4"
            assert client.get(location).json()["status"] == "running"
            assert timeout == settings.document_job_timeout_seconds
            return True, "imported"

    assert await process_next(repository, Parser())
    final = client.get(location).json()
    assert final["status"] == "completed"
    assert final["attempts"] == 1
    assert client.post(f"{location}/retry").status_code == 409


@pytest.mark.asyncio
async def test_timeout_and_retry_limit(job_api):
    client, repository = job_api
    location = submit_pdf(client).headers["location"]

    class TimedOutParser:
        async def run(self, path, *, timeout):
            raise TimeoutError

    assert await process_next(repository, TimedOutParser())
    assert client.get(location).json()["error"] == "Document processing timed out."
    retry = client.post(f"{location}/retry")
    assert retry.status_code == 202
    assert retry.json()["status"] == "queued"
    assert await process_next(repository, TimedOutParser())
    assert client.get(location).json()["attempts"] == 2
    assert client.post(f"{location}/retry").status_code == 409


def test_recovery_preserves_queued_jobs_and_marks_interrupted_job_failed(job_api):
    client, repository = job_api
    first = submit_pdf(client).json()
    second = submit_pdf(client).json()
    interrupted, _ = repository.claim()

    reopened = DocumentJobRepository(repository.path)
    with reopened.worker_lock():
        reopened.recover_interrupted()
    for job in (first, second):
        expected = "failed" if job["id"] == str(interrupted.id) else "queued"
        assert reopened.get(job["id"]).status == expected


def test_concurrent_claims_cannot_take_same_job(job_api):
    client, repository = job_api
    assert submit_pdf(client).status_code == 202
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: repository.claim(), range(2)))
    assert sum(claim is not None for claim in claims) == 1


def test_invalid_uploads_and_unknown_jobs(job_api, monkeypatch):
    client, repository = job_api
    assert client.post("/document-jobs", files={"file": ("fake.pdf", b"text")}).status_code == 400
    monkeypatch.setattr(settings, "document_job_max_bytes", 4)
    assert submit_pdf(client).status_code == 413
    assert repository.claim() is None
    assert client.get(f"/document-jobs/{uuid4()}").status_code == 404
    monkeypatch.setattr(settings, "document_parser_enabled", False)
    assert submit_pdf(client).status_code == 503


def test_readiness_reports_unavailable_neo4j(monkeypatch):
    class UnavailableDriver:
        def session(self, *, database):
            raise ServiceUnavailable("connection refused")

    async def get_driver():
        return UnavailableDriver()

    monkeypatch.setattr(main, "get_driver", get_driver)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
