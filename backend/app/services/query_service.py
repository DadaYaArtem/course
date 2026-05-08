from collections.abc import Mapping
from typing import Any, Protocol

from fastapi import Depends

from app.repositories.graph_repository import GraphRepository, get_graph_repository
from app.schemas.llm import LLMGenerationResult
from app.schemas.query import QueryServiceResult, QueryType
from app.services.classifier import QueryClassifier
from app.services.llm_client import GeminiLLMClient, get_llm_client
from app.services.prompt_builder import PromptBuilder


class LLMClientProtocol(Protocol):
    """Protocol for LLM clients used by QueryService."""

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Generate text from a prepared prompt."""


class QueryService:
    """Orchestrate classification, retrieval, prompt building, and LLM calls."""

    def __init__(
        self,
        repository: GraphRepository,
        classifier: QueryClassifier | None = None,
        prompt_builder: PromptBuilder | None = None,
        llm_client: LLMClientProtocol | None = None,
    ) -> None:
        """Initialize the query orchestration service.

        Args:
            repository: Graph repository used for Neo4j retrieval.
            classifier: Optional query classifier dependency.
            prompt_builder: Optional prompt builder dependency.
            llm_client: Optional LLM client dependency.
        """
        self._repository = repository
        self._classifier = classifier or QueryClassifier()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._llm_client = llm_client or GeminiLLMClient()

    async def answer(self, text: str, language: str = "ru") -> QueryServiceResult:
        """Answer a user question using graph context and the LLM.

        Args:
            text: Raw user question.
            language: Response language code ("ru" or "en").

        Returns:
            Structured answer metadata for the API layer.
        """
        classification = await self._classifier.classify_with_llm_fallback(
            text=text,
            llm_client=self._llm_client,
        )
        context = await self._build_context(
            classification.query_type,
            classification.entities,
        )
        prompt_result = self._prompt_builder.build(
            query_type=classification.query_type,
            user_question=text,
            context=context,
            language=language,
        )
        llm_result = await self._llm_client.generate(prompt_result.prompt)
        return QueryServiceResult(
            answer=llm_result.text,
            source_entities=classification.entities,
            query_type=classification.query_type,
            from_kb=not prompt_result.warning,
            classification_source=classification.classification_source,
        )

    async def _build_context(
        self,
        query_type: QueryType,
        entities: list[str],
    ) -> dict[str, Any]:
        """Build structured retrieval context for a classified query."""
        if query_type == QueryType.DEFINITION:
            return await self._definition_context(entities)
        if query_type == QueryType.COMPARISON:
            return await self._comparison_context(entities)
        if query_type == QueryType.CAPABILITIES:
            return await self._capabilities_context(entities)
        if query_type == QueryType.METHODS:
            return await self._methods_context(entities)
        if query_type == QueryType.RECOMMENDATION:
            return await self._recommendation_context(entities)
        return await self._unknown_context(entities)

    async def _definition_context(self, entities: list[str]) -> dict[str, Any]:
        """Build context for definition questions."""
        entity = self._first_entity(entities)
        if entity is None:
            return {}

        matches = await self._repository.find_entity(entity)
        definition = await self._repository.get_definition(entity)
        neighbors = await self._repository.get_neighbors(entity)
        return self._compact_context(
            {
                "entity": entity,
                "matches": matches,
                "definition": definition,
                "neighbors": neighbors,
            }
        )

    async def _comparison_context(self, entities: list[str]) -> dict[str, Any]:
        """Build context for comparison questions."""
        if len(entities) < 2:
            return {}

        comparison = await self._repository.compare_models(entities[0], entities[1])
        return self._compact_context(
            {
                "entities": entities[:2],
                "comparison": comparison,
            }
        )

    async def _capabilities_context(self, entities: list[str]) -> dict[str, Any]:
        """Build context for model capability questions."""
        entity = self._first_entity(entities)
        if entity is None:
            return {}

        tasks = await self._repository.get_model_tasks(entity)
        neighbors = await self._repository.get_neighbors(entity)
        return self._compact_context(
            {
                "entity": entity,
                "tasks": tasks,
                "neighbors": neighbors,
            }
        )

    async def _methods_context(self, entities: list[str]) -> dict[str, Any]:
        """Build context for method questions."""
        entity = self._first_entity(entities)
        if entity is None:
            return {}

        methods = await self._repository.get_model_methods(entity)
        neighbors = await self._repository.get_neighbors(entity)
        return self._compact_context(
            {
                "entity": entity,
                "methods": methods,
                "neighbors": neighbors,
            }
        )

    async def _recommendation_context(self, entities: list[str]) -> dict[str, Any]:
        """Build context for recommendation questions."""
        searches = {}
        for entity in entities:
            matches = await self._repository.search_entities(entity)
            if matches:
                searches[entity] = matches

        return self._compact_context(
            {
                "entities": entities,
                "search_results": searches,
            }
        )

    async def _unknown_context(self, entities: list[str]) -> dict[str, Any]:
        """Build best-effort context for unknown query types."""
        entity = self._first_entity(entities)
        if entity is None:
            return {}

        matches = await self._repository.find_entity(entity)
        neighbors = await self._repository.get_neighbors(entity)
        return self._compact_context(
            {
                "entity": entity,
                "matches": matches,
                "neighbors": neighbors,
            }
        )

    def _first_entity(self, entities: list[str]) -> str | None:
        """Return the first extracted entity if present."""
        return entities[0] if entities else None

    def _compact_context(self, context: Mapping[str, Any]) -> dict[str, Any]:
        """Drop empty context fields so prompt fallback can detect no context."""
        compacted = {
            key: value
            for key, value in context.items()
            if value not in (None, [], {}, "")
        }
        has_retrieved_data = any(
            key not in {"entity", "entities"} for key in compacted
        )
        if not has_retrieved_data:
            return {}
        return compacted


async def get_query_service(
    repository: GraphRepository = Depends(get_graph_repository),
    llm_client: LLMClientProtocol = Depends(get_llm_client),
) -> QueryService:
    """FastAPI dependency that injects QueryService."""
    return QueryService(repository=repository, llm_client=llm_client)
