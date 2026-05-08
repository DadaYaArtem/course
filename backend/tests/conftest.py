import asyncio
import sys

import pytest_asyncio
from neo4j import AsyncGraphDatabase, AsyncDriver

from app.core.config import settings
from app.repositories.graph_repository import GraphRepository


if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest_asyncio.fixture
async def driver() -> AsyncDriver:
    """Create a real Neo4j AsyncDriver for the current test loop."""
    drv = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    yield drv
    await drv.close()


@pytest_asyncio.fixture
async def repo(driver: AsyncDriver) -> GraphRepository:
    """Return a GraphRepository backed by the real driver."""
    return GraphRepository(driver)
