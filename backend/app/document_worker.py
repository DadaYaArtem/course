import asyncio
import logging
import signal
import sqlite3
import sys

from app.core.config import settings
from app.core.logging import setup_logging
from app.repositories.document_jobs import DocumentJobRepository, get_document_job_repository
from app.services.document_service import LocalParserPipeline

logger = logging.getLogger(__name__)


async def process_next(repository: DocumentJobRepository, parser: LocalParserPipeline) -> bool:
    claimed = repository.claim()
    if claimed is None:
        return False
    job, path = claimed
    job_id = str(job.id)
    logger.info("Processing document job %s, attempt %s", job_id, job.attempts)
    error = None
    try:
        indexed, _ = await parser.run(path, timeout=settings.document_job_timeout_seconds)
        if not indexed:
            error = "Document parser did not perform indexing."
    except TimeoutError:
        error = "Document processing timed out."
    except asyncio.CancelledError:
        repository.finish(job_id, "Document processing was interrupted.")
        raise
    except Exception as exc:
        logger.warning("Document job %s failed (%s)", job_id, type(exc).__name__)
        error = "Document processing failed. Check the file and deployment."
    repository.finish(job_id, error)
    logger.info("Document job %s finished with status %s", job_id, "failed" if error else "completed")
    return True


async def run_worker() -> None:
    setup_logging()
    if not settings.document_parser_enabled:
        logger.info("Document processing is disabled.")
        return
    repository = get_document_job_repository()
    parser = LocalParserPipeline()
    if sys.platform != "win32":
        task = asyncio.current_task()
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    with repository.worker_lock():
        repository.recover_interrupted()
        while True:
            if not await process_next(repository, parser):
                await asyncio.sleep(1)


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    except sqlite3.Error:
        logger.exception("Document worker could not access or lock its SQLite storage.")
        raise SystemExit(1)
