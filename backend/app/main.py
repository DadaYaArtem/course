import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from neo4j.exceptions import DriverError, Neo4jError

from app.core.config import settings
from app.core.database import close_driver, get_driver
from app.core.exception_handlers import (
    app_error_handler,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.exceptions import AppError
from app.core.logging import setup_logging
from app.routers import document_jobs, documents, query

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown."""
    setup_logging()
    await get_driver()
    logger.info("Application startup complete")
    yield
    await close_driver()
    logger.info("Application shutdown complete")


app = FastAPI(
    title="RAG Knowledge Base API",
    description="Graph-based RAG backend for AI technologies knowledge base.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}


@app.get("/ready", tags=["health"])
async def readiness() -> dict[str, str]:
    """Check that the configured Neo4j database accepts read queries."""
    driver = await get_driver()
    try:
        async with asyncio.timeout(3):
            async with driver.session(database=settings.neo4j_database) as session:
                result = await session.run("RETURN 1")
                await result.consume()
    except (DriverError, Neo4jError, TimeoutError) as exc:
        raise HTTPException(503, "Neo4j is not ready.") from exc
    return {"status": "ready"}


app.include_router(query.router)
app.include_router(documents.router)
app.include_router(document_jobs.router)
