import pytest

from app.schemas.query import QueryType
from app.services.classifier import QueryClassifier, classify_query


@pytest.fixture
def classifier() -> QueryClassifier:
    """Return a rule-based query classifier."""
    return QueryClassifier()


@pytest.mark.parametrize(
    ("text", "expected_type", "expected_entities"),
    [
        ("Что такое Transformer?", QueryType.DEFINITION, ["Transformer"]),
        ("What is Retrieval-Augmented Generation?", QueryType.DEFINITION, ["Retrieval-Augmented Generation"]),
        ("Чем BERT отличается от GPT?", QueryType.COMPARISON, ["BERT", "GPT"]),
        ("Compare RoBERTa vs BERT", QueryType.COMPARISON, ["RoBERTa", "BERT"]),
        ("Для чего используется LLaMA?", QueryType.CAPABILITIES, ["LLaMA"]),
        ("What is GPT used for?", QueryType.CAPABILITIES, ["GPT"]),
        ("Какие методы использует BERT?", QueryType.METHODS, ["BERT"]),
        ("Which methods does RoBERTa use?", QueryType.METHODS, ["RoBERTa"]),
        ("Какой фреймворк выбрать для NLP?", QueryType.RECOMMENDATION, ["NLP"]),
        ("Which framework should I choose for NLP?", QueryType.RECOMMENDATION, ["NLP"]),
    ],
)
def test_classify_supported_query_types(
    classifier: QueryClassifier,
    text: str,
    expected_type: QueryType,
    expected_entities: list[str],
) -> None:
    """Classifier covers all required query types in Russian and English."""
    result = classifier.classify(text)

    assert result.query_type == expected_type
    assert result.entities == expected_entities


def test_classify_unknown_query(classifier: QueryClassifier) -> None:
    """Classifier returns unknown when no rule matches."""
    result = classifier.classify("Hello, can you help me?")

    assert result.query_type == QueryType.UNKNOWN
    assert result.entities == []


def test_classify_query_helper_uses_default_classifier() -> None:
    """Convenience function returns a classification result."""
    result = classify_query("Что такое BERT?")

    assert result.query_type == QueryType.DEFINITION
    assert result.entities == ["BERT"]


def test_extraction_deduplicates_entities(classifier: QueryClassifier) -> None:
    """Entity extraction preserves order and removes duplicates."""
    result = classifier.classify("Compare BERT vs BERT and GPT")

    assert result.query_type == QueryType.COMPARISON
    assert result.entities == ["BERT", "GPT"]
