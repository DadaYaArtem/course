from typing import Any

import pytest

from app.schemas.llm import LLMGenerationResult
from app.schemas.query import QueryType
from app.services.query_service import QueryService


class FakeRepository:
    """In-memory repository test double for QueryService tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def find_entity(self, term: str) -> list[dict[str, Any]]:
        """Return fake exact entity matches."""
        self.calls.append(("find_entity", (term,)))
        if term == "BERT":
            return [{"labels": ["Model"], "name": "BERT", "props": {"name": "BERT"}}]
        return []

    async def search_entities(self, q: str) -> list[dict[str, Any]]:
        """Return fake search matches."""
        self.calls.append(("search_entities", (q,)))
        if q == "NLP":
            return [{"labels": ["Task"], "name": "Question Answering"}]
        return []

    async def get_definition(self, concept: str) -> dict[str, Any] | None:
        """Return fake concept definition."""
        self.calls.append(("get_definition", (concept,)))
        if concept == "Transformer":
            return {"concept": "Transformer", "description": "Attention architecture"}
        return None

    async def get_neighbors(self, name: str) -> list[dict[str, Any]]:
        """Return fake direct neighbors."""
        self.calls.append(("get_neighbors", (name,)))
        if name in {"BERT", "Transformer"}:
            return [{"center": name, "rel": "IS_A", "neighbor": "Transformer"}]
        return []

    async def get_model_tasks(self, model: str) -> dict[str, Any] | None:
        """Return fake model tasks."""
        self.calls.append(("get_model_tasks", (model,)))
        if model == "BERT":
            return {"model": "BERT", "tasks": ["Question Answering"]}
        return None

    async def get_model_methods(self, model: str) -> dict[str, Any] | None:
        """Return fake model methods."""
        self.calls.append(("get_model_methods", (model,)))
        if model == "BERT":
            return {"model": "BERT", "methods": ["Fine-tuning"]}
        return None

    async def compare_models(self, a: str, b: str) -> dict[str, Any] | None:
        """Return fake model comparison."""
        self.calls.append(("compare_models", (a, b)))
        if (a, b) == ("BERT", "GPT"):
            return {
                "model_a": "BERT",
                "tasks_a": ["Question Answering"],
                "methods_a": ["Masked Language Modeling"],
                "model_b": "GPT",
                "tasks_b": ["Machine Translation"],
                "methods_b": [],
            }
        return None


class FakeLLMClient:
    """LLM test double that records prompts."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Return a fake LLM result."""
        self.prompts.append(prompt)
        return LLMGenerationResult(
            text="Generated answer",
            latency_ms=1.0,
            model="fake-llm",
        )


@pytest.mark.asyncio
async def test_answer_definition_uses_repository_context() -> None:
    """QueryService orchestrates definition retrieval and LLM generation."""
    repository = FakeRepository()
    llm_client = FakeLLMClient()
    service = QueryService(repository=repository, llm_client=llm_client)

    result = await service.answer("What is Transformer?")

    assert result.answer == "Generated answer"
    assert result.query_type == QueryType.DEFINITION
    assert result.source_entities == ["Transformer"]
    assert result.from_kb is True
    assert ("get_definition", ("Transformer",)) in repository.calls
    assert "Attention architecture" in llm_client.prompts[0]


@pytest.mark.asyncio
async def test_answer_comparison_uses_compare_models() -> None:
    """QueryService uses comparison repository query for comparison intent."""
    repository = FakeRepository()
    llm_client = FakeLLMClient()
    service = QueryService(repository=repository, llm_client=llm_client)

    result = await service.answer("Compare BERT vs GPT")

    assert result.query_type == QueryType.COMPARISON
    assert result.source_entities == ["BERT", "GPT"]
    assert result.from_kb is True
    assert ("compare_models", ("BERT", "GPT")) in repository.calls
    assert "Question Answering" in llm_client.prompts[0]


@pytest.mark.asyncio
async def test_answer_capabilities_uses_model_tasks() -> None:
    """QueryService uses model task retrieval for capability intent."""
    repository = FakeRepository()
    service = QueryService(repository=repository, llm_client=FakeLLMClient())

    result = await service.answer("What is BERT used for?")

    assert result.query_type == QueryType.CAPABILITIES
    assert result.from_kb is True
    assert ("get_model_tasks", ("BERT",)) in repository.calls


@pytest.mark.asyncio
async def test_answer_methods_uses_model_methods() -> None:
    """QueryService uses model method retrieval for methods intent."""
    repository = FakeRepository()
    service = QueryService(repository=repository, llm_client=FakeLLMClient())

    result = await service.answer("Which methods does BERT use?")

    assert result.query_type == QueryType.METHODS
    assert result.from_kb is True
    assert ("get_model_methods", ("BERT",)) in repository.calls


@pytest.mark.asyncio
async def test_answer_recommendation_uses_search() -> None:
    """QueryService uses search for recommendation intent."""
    repository = FakeRepository()
    service = QueryService(repository=repository, llm_client=FakeLLMClient())

    result = await service.answer("Which framework should I choose for NLP?")

    assert result.query_type == QueryType.RECOMMENDATION
    assert result.from_kb is True
    assert ("search_entities", ("NLP",)) in repository.calls


@pytest.mark.asyncio
async def test_answer_empty_context_marks_not_from_kb() -> None:
    """QueryService marks results as not from KB when retrieval is empty."""
    repository = FakeRepository()
    llm_client = FakeLLMClient()
    service = QueryService(repository=repository, llm_client=llm_client)

    result = await service.answer("What is UnknownModel?")

    assert result.query_type == QueryType.DEFINITION
    assert result.source_entities == ["UnknownModel"]
    assert result.from_kb is False
    assert "No Neo4j knowledge-base context was found" in llm_client.prompts[0]
