import logging
from typing import Any, TypedDict

from fastapi import Depends
from neo4j import AsyncDriver
from neo4j.exceptions import Neo4jError

from app.core.exceptions import Neo4jConnectionError
from app.core.database import get_driver
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Return-type definitions
# ---------------------------------------------------------------------------

class EntityResult(TypedDict):
    """Single entity found by exact or alias match (Q1)."""

    labels: list[str]
    name: str
    props: dict[str, Any]


class SearchResult(TypedDict):
    """Entity found by substring search (Q2)."""

    labels: list[str]
    name: str


class DefinitionResult(TypedDict):
    """Concept name and description (Q3)."""

    concept: str
    description: str | None


class NeighborResult(TypedDict):
    """One neighbour edge in the local subgraph (Q4)."""

    center: str
    rel: str
    neighbor_type: list[str]
    neighbor: str


class ModelTasksResult(TypedDict):
    """Tasks a model is USED_FOR (Q5)."""

    model: str
    tasks: list[str]


class ModelMethodsResult(TypedDict):
    """Methods a model USES (Q6)."""

    model: str
    methods: list[str]


class CompareModelsResult(TypedDict):
    """Side-by-side comparison of two models (Q8)."""

    model_a: str
    tasks_a: list[str]
    methods_a: list[str]
    model_b: str
    tasks_b: list[str]
    methods_b: list[str]


class DocumentSourceResult(TypedDict):
    """Indexed document source found in Neo4j."""

    source: str


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------

class GraphRepository:
    """Data-access layer: all Neo4j queries live here, no business logic."""

    def __init__(self, driver: AsyncDriver) -> None:
        self._driver = driver
        self._db = settings.neo4j_database

    async def _run_query(self, query: str, **params: Any) -> list[dict[str, Any]]:
        """Run a Cypher query and convert driver errors to app errors."""
        try:
            async with self._driver.session(database=self._db) as session:
                result = await session.run(query, **params)
                return await result.data()
        except Neo4jError as exc:
            logger.exception("Neo4j query failed")
            raise Neo4jConnectionError("Neo4j query failed.") from exc

    # Q1
    async def find_entity(self, term: str) -> list[EntityResult]:
        """Find entity by exact name, normalized_name, or alias.

        Args:
            term: The search term (exact match).

        Returns:
            List of matched entity records.
        """
        query = """
        MATCH (n)
        WHERE n.name = $term
           OR n.normalized_name = toLower($term)
           OR $term IN coalesce(n.aliases, [])
        RETURN labels(n) AS labels, n.name AS name, properties(n) AS props
        """
        records = await self._run_query(query, term=term)
        logger.debug("find_entity(%r) → %d row(s)", term, len(records))
        return [
            EntityResult(labels=r["labels"], name=r["name"], props=r["props"])
            for r in records
        ]

    # Q2
    async def search_entities(self, q: str) -> list[SearchResult]:
        """Search entities by case-insensitive substring.

        Args:
            q: Substring to search in name / normalized_name.

        Returns:
            Up to 20 matched entities ordered by name.
        """
        query = """
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($q)
           OR toLower(coalesce(n.normalized_name, '')) CONTAINS toLower($q)
        RETURN labels(n) AS labels, n.name AS name
        ORDER BY name
        LIMIT 20
        """
        records = await self._run_query(query, q=q)
        logger.debug("search_entities(%r) → %d row(s)", q, len(records))
        return [SearchResult(labels=r["labels"], name=r["name"]) for r in records]

    # Q3
    async def get_definition(self, concept: str) -> DefinitionResult | None:
        """Return the description of a Concept node.

        Args:
            concept: Concept name, normalized_name, or alias.

        Returns:
            DefinitionResult or None if concept is not found.
        """
        query = """
        MATCH (c:Concept)
        WHERE c.name = $concept
           OR c.normalized_name = toLower($concept)
           OR $concept IN coalesce(c.aliases, [])
        RETURN c.name AS concept, c.description AS description
        """
        records = await self._run_query(query, concept=concept)
        if not records:
            logger.debug("get_definition(%r) → not found", concept)
            return None
        r = records[0]
        return DefinitionResult(concept=r["concept"], description=r["description"])

    # Q4
    async def get_neighbors(self, name: str) -> list[NeighborResult]:
        """Return all direct neighbours of a node (depth = 1).

        Args:
            name: Node name, normalized_name, or alias.

        Returns:
            List of neighbour edge descriptions.
        """
        query = """
        MATCH (n)
        WHERE n.name = $name
           OR n.normalized_name = toLower($name)
           OR $name IN coalesce(n.aliases, [])
        MATCH (n)-[r]-(m)
        RETURN n.name AS center, type(r) AS rel,
               labels(m) AS neighborType, m.name AS neighbor
        LIMIT 50
        """
        records = await self._run_query(query, name=name)
        logger.debug("get_neighbors(%r) → %d row(s)", name, len(records))
        return [
            NeighborResult(
                center=r["center"],
                rel=r["rel"],
                neighbor_type=r["neighborType"],
                neighbor=r["neighbor"],
            )
            for r in records
        ]

    # Q5
    async def get_model_tasks(self, model: str) -> ModelTasksResult | None:
        """Return tasks a model is USED_FOR.

        Args:
            model: Model name, normalized_name, or alias.

        Returns:
            ModelTasksResult or None if model is not found.
        """
        query = """
        MATCH (m:Model)
        WHERE m.name = $model
           OR m.normalized_name = toLower($model)
           OR $model IN coalesce(m.aliases, [])
        MATCH (m)-[:USED_FOR]->(t:Task)
        RETURN m.name AS model, collect(DISTINCT t.name) AS tasks
        """
        records = await self._run_query(query, model=model)
        if not records:
            logger.debug("get_model_tasks(%r) → not found", model)
            return None
        r = records[0]
        return ModelTasksResult(model=r["model"], tasks=r["tasks"])

    # Q6
    async def get_model_methods(self, model: str) -> ModelMethodsResult | None:
        """Return methods a model USES.

        Args:
            model: Model name, normalized_name, or alias.

        Returns:
            ModelMethodsResult or None if model is not found.
        """
        query = """
        MATCH (m:Model)
        WHERE m.name = $model
           OR m.normalized_name = toLower($model)
           OR $model IN coalesce(m.aliases, [])
        MATCH (m)-[:USES]->(me:Method)
        RETURN m.name AS model, collect(DISTINCT me.name) AS methods
        """
        records = await self._run_query(query, model=model)
        if not records:
            logger.debug("get_model_methods(%r) → not found", model)
            return None
        r = records[0]
        return ModelMethodsResult(model=r["model"], methods=r["methods"])

    # Q8
    async def compare_models(self, a: str, b: str) -> CompareModelsResult | None:
        """Compare two models by their tasks and methods.

        Args:
            a: First model name.
            b: Second model name.

        Returns:
            CompareModelsResult or None if either model is not found.
        """
        query = """
        MATCH (a:Model {name: $a})
        OPTIONAL MATCH (a)-[:USED_FOR]->(ta:Task)
        OPTIONAL MATCH (a)-[:USES]->(ma:Method)
        WITH a, collect(DISTINCT ta.name) AS tasksA, collect(DISTINCT ma.name) AS methodsA
        MATCH (b:Model {name: $b})
        OPTIONAL MATCH (b)-[:USED_FOR]->(tb:Task)
        OPTIONAL MATCH (b)-[:USES]->(mb:Method)
        RETURN
          a.name AS modelA, tasksA AS tasksA, methodsA AS methodsA,
          b.name AS modelB,
          collect(DISTINCT tb.name) AS tasksB,
          collect(DISTINCT mb.name) AS methodsB
        """
        records = await self._run_query(query, a=a, b=b)
        if not records:
            logger.debug("compare_models(%r, %r) → not found", a, b)
            return None
        r = records[0]
        return CompareModelsResult(
            model_a=r["modelA"],
            tasks_a=r["tasksA"],
            methods_a=r["methodsA"],
            model_b=r["modelB"],
            tasks_b=r["tasksB"],
            methods_b=r["methodsB"],
        )

    # Q9
    async def entity_exists(self, name: str) -> bool:
        """Check whether any node with the given name exists.

        Args:
            name: Exact node name.

        Returns:
            True if at least one node found, False otherwise.
        """
        query = """
        MATCH (n {name: $name})
        RETURN count(n) AS exists_count
        """
        records = await self._run_query(query, name=name)
        exists = bool(records and records[0]["exists_count"] > 0)
        logger.debug("entity_exists(%r) → %s", name, exists)
        return exists


    async def list_sources(self) -> list[DocumentSourceResult]:
        """Return distinct source names indexed in the graph.

        Returns:
            Source names from node and relationship source properties.
        """
        query = """
        CALL {
            MATCH (n)
            WHERE n.source IS NOT NULL
            RETURN n.source AS source
            UNION
            MATCH ()-[r]->()
            WHERE r.source IS NOT NULL
            RETURN r.source AS source
        }
        RETURN DISTINCT source
        ORDER BY source
        """
        records = await self._run_query(query)
        logger.debug("list_sources() -> %d row(s)", len(records))
        return [DocumentSourceResult(source=r["source"]) for r in records]


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_graph_repository(
    driver: AsyncDriver = Depends(get_driver),
) -> GraphRepository:
    """FastAPI dependency that injects GraphRepository into route handlers."""
    return GraphRepository(driver)
