import logging

from neo4j import AsyncDriver, AsyncGraphDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    """Return the singleton AsyncDriver, creating it on first call."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        logger.info("Neo4j AsyncDriver created: %s", settings.neo4j_uri)
    return _driver


async def close_driver() -> None:
    """Close the singleton AsyncDriver if it is open."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None
        logger.info("Neo4j AsyncDriver closed")
