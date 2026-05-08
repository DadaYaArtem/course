import pytest

from app.schemas.query import QueryType
from app.services.prompt_builder import PromptBuilder, build_prompt


@pytest.fixture
def builder() -> PromptBuilder:
    """Return a prompt builder."""
    return PromptBuilder()


@pytest.mark.parametrize(
    ("query_type", "expected_phrase"),
    [
        (QueryType.DEFINITION, "define the requested entity"),
        (QueryType.COMPARISON, "compare the requested entities"),
        (QueryType.CAPABILITIES, "what the requested model or concept is used for"),
        (QueryType.METHODS, "methods or techniques used by the requested entity"),
        (QueryType.RECOMMENDATION, "make a recommendation"),
    ],
)
def test_build_uses_query_type_template(
    builder: PromptBuilder,
    query_type: QueryType,
    expected_phrase: str,
) -> None:
    """Prompt builder uses a dedicated template for each supported type."""
    result = builder.build(
        query_type=query_type,
        user_question="What is BERT?",
        context={"entity": {"name": "BERT"}},
    )

    assert result.warning is False
    assert expected_phrase in result.prompt
    assert f"Query type: {query_type.value}" in result.prompt
    assert "User question: What is BERT?" in result.prompt
    assert '"name": "BERT"' in result.prompt


def test_build_serializes_structured_context(builder: PromptBuilder) -> None:
    """Prompt includes structured Neo4j context as stable JSON."""
    context = {
        "entity": {"name": "BERT", "labels": ["Model"]},
        "relations": [{"type": "USED_FOR", "target": "Question Answering"}],
    }

    result = builder.build(
        query_type=QueryType.CAPABILITIES,
        user_question="What is BERT used for?",
        context=context,
    )

    assert result.warning is False
    assert "Neo4j context:" in result.prompt
    assert '"relations": [' in result.prompt
    assert '"type": "USED_FOR"' in result.prompt
    assert '"target": "Question Answering"' in result.prompt


def test_build_empty_context_returns_warning_prompt(builder: PromptBuilder) -> None:
    """Empty context returns a fallback prompt and warning flag."""
    result = builder.build(
        query_type=QueryType.DEFINITION,
        user_question="What is UnknownModel?",
        context={},
    )

    assert result.warning is True
    assert "No Neo4j knowledge-base context was found" in result.prompt
    assert "Neo4j context:" not in result.prompt
    assert "User question: What is UnknownModel?" in result.prompt


def test_build_none_context_returns_warning_prompt(builder: PromptBuilder) -> None:
    """None context is treated the same as empty context."""
    result = builder.build(
        query_type=QueryType.UNKNOWN,
        user_question="Can you help?",
        context=None,
    )

    assert result.warning is True
    assert "intent is unclear" in result.prompt


def test_build_prompt_helper_uses_default_builder() -> None:
    """Convenience function returns a prompt build result."""
    result = build_prompt(
        query_type=QueryType.METHODS,
        user_question="Which methods does BERT use?",
        context={"methods": ["Fine-tuning"]},
    )

    assert result.warning is False
    assert "Fine-tuning" in result.prompt
