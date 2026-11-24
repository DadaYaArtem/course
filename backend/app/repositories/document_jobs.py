import sqlite3
from contextlib import closing, contextmanager
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from app.core.config import settings
from app.schemas.document_jobs import DocumentJob

NOW = "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"


class DocumentJobRepository:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as connection:
            connection.execute(f"""
                CREATE TABLE IF NOT EXISTS document_jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT ({NOW}),
                    updated_at TEXT NOT NULL DEFAULT ({NOW}),
                    error TEXT
                )
            """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS document_jobs_queue
                ON document_jobs (status, updated_at, id)
            """)

    @contextmanager
    def connection(self):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.row_factory = sqlite3.Row
            yield connection

    @contextmanager
    def worker_lock(self):
        """Hold a process lock in a separate SQLite database until the worker exits."""
        with closing(sqlite3.connect(self.path.with_suffix(".worker.sqlite3"), timeout=0)) as lock:
            lock.execute("BEGIN EXCLUSIVE")
            yield

    def create(self, filename: str, path: Path, max_attempts: int) -> DocumentJob:
        with self.connection() as connection:
            row = connection.execute("""
                INSERT INTO document_jobs (id, filename, path, status, max_attempts)
                VALUES (?, ?, ?, 'queued', ?) RETURNING *
            """, (str(uuid4()), filename, str(path), max_attempts)).fetchone()
        return DocumentJob.model_validate(dict(row))

    def get(self, job_id: str) -> DocumentJob | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM document_jobs WHERE id = ?", (job_id,)
            ).fetchone()
        return DocumentJob.model_validate(dict(row)) if row is not None else None

    def retry(self, job_id: str) -> DocumentJob | None:
        with self.connection() as connection:
            row = connection.execute(f"""
                UPDATE document_jobs SET status = 'queued', error = NULL, updated_at = {NOW}
                WHERE id = ? AND status = 'failed' AND attempts < max_attempts
                RETURNING *
            """, (job_id,)).fetchone()
        return DocumentJob.model_validate(dict(row)) if row is not None else None

    def claim(self) -> tuple[DocumentJob, Path] | None:
        with self.connection() as connection:
            row = connection.execute(f"""
                UPDATE document_jobs
                SET status = 'running', attempts = attempts + 1, updated_at = {NOW}
                WHERE id = (
                    SELECT id FROM document_jobs WHERE status = 'queued'
                    ORDER BY updated_at, id LIMIT 1
                )
                RETURNING *
            """).fetchone()
        if row is None:
            return None
        return DocumentJob.model_validate(dict(row)), Path(row["path"])

    def finish(self, job_id: str, error: str | None) -> None:
        with self.connection() as connection:
            connection.execute(f"""
                UPDATE document_jobs SET status = ?, error = ?, updated_at = {NOW}
                WHERE id = ? AND status = 'running'
            """, ("failed" if error else "completed", error, job_id))

    def recover_interrupted(self) -> None:
        with self.connection() as connection:
            connection.execute(f"""
                UPDATE document_jobs
                SET status = 'failed', error = ?, updated_at = {NOW}
                WHERE status = 'running'
            """, ("Worker stopped before the result was recorded.",))


@lru_cache(maxsize=1)
def get_document_job_repository() -> DocumentJobRepository:
    upload_dir = Path(settings.document_upload_dir).resolve()
    return DocumentJobRepository(upload_dir / ".jobs" / "jobs.sqlite3")
