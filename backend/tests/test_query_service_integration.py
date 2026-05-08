import pytest

from app.repositories.graph_repository import GraphRepository
from app.schemas.llm import LLMGenerationResult
from app.schemas.query import QueryType
from app.services.query_service import QueryService


class RecordingLLMClient:
    """LLM test double that records prompts while avoiding network calls."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Record the prompt and return a deterministic answer."""
        self.prompts.append(prompt)
        return LLMGenerationResult(
            text="Mocked integration answer",
            latency_ms=1.0,
            model="mock-llm",
        )


@pytest.mark.asyncio
async def test_query_service_integration_uses_real_neo4j_context(
    repo: GraphRepository,
) -> None:
    """QueryService integrates classifier, real Neo4j, prompt builder, and mocked LLM."""
    llm_client = RecordingLLMClient()
    service = QueryService(repository=repo, llm_client=llm_client)

    result = await service.answer("What is BERT used for?")

    assert result.answer == "Mocked integration answer"
    assert result.query_type == QueryType.CAPABILITIES
    assert result.source_entities == ["BERT"]
    assert result.from_kb is True
    assert "Question Answering" in llm_client.prompts[0]
    assert "Text Classification" in llm_client.prompts[0]


@pytest.mark.asyncio
async def test_query_service_integration_marks_missing_context_not_from_kb(
    repo: GraphRepository,
) -> None:
    """QueryService uses fallback prompt when real Neo4j has no matching context."""
    llm_client = RecordingLLMClient()
    service = QueryService(repository=repo, llm_client=llm_client)

    result = await service.answer("What is UnknownModel?")

    assert result.answer == "Mocked integration answer"
    assert result.query_type == QueryType.DEFINITION
    assert result.source_entities == ["UnknownModel"]
    assert result.from_kb is False
    assert "No Neo4j knowledge-base context was found" in llm_client.prompts[0]
