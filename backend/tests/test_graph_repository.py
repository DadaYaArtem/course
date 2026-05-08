"""Integration tests for GraphRepository.

Requires a running Neo4j instance with seed data loaded.
Run: docker compose up -d neo4j  (then apply constraints.cypher + seed.cypher)
Then: cd backend && pytest tests/test_graph_repository.py -v
"""
import pytest
from app.repositories.graph_repository import GraphRepository


# ---------------------------------------------------------------------------
# Q1 — find_entity
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_entity_exact_name(repo: GraphRepository) -> None:
    results = await repo.find_entity("BERT")
    assert len(results) > 0
    assert results[0]["name"] == "BERT"
    assert "Model" in results[0]["labels"]


@pytest.mark.asyncio
async def test_find_entity_by_alias(repo: GraphRepository) -> None:
    # RoBERTa has alias "robustly optimized bert approach" in seed
    results = await repo.find_entity("robustly optimized bert approach")
    assert len(results) > 0
    assert results[0]["name"] == "RoBERTa"


@pytest.mark.asyncio
async def test_find_entity_not_found(repo: GraphRepository) -> None:
    results = await repo.find_entity("__nonexistent_entity_xyz__")
    assert results == []


# ---------------------------------------------------------------------------
# Q2 — search_entities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_entities_partial(repo: GraphRepository) -> None:
    results = await repo.search_entities("bert")
    names = [r["name"] for r in results]
    assert any("BERT" in n or "RoBERTa" in n for n in names)


@pytest.mark.asyncio
async def test_search_entities_empty(repo: GraphRepository) -> None:
    results = await repo.search_entities("__no_match_xyz__")
    assert results == []


# ---------------------------------------------------------------------------
# Q3 — get_definition
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_definition_found(repo: GraphRepository) -> None:
    result = await repo.get_definition("Transformer")
    assert result is not None
    assert result["concept"] == "Transformer"
    assert result["description"] is not None
    assert len(result["description"]) > 0


@pytest.mark.asyncio
async def test_get_definition_not_found(repo: GraphRepository) -> None:
    result = await repo.get_definition("__unknown_concept__")
    assert result is None


# ---------------------------------------------------------------------------
# Q4 — get_neighbors
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_neighbors_bert(repo: GraphRepository) -> None:
    results = await repo.get_neighbors("BERT")
    assert len(results) > 0
    rels = {r["rel"] for r in results}
    # BERT has USED_FOR, USES, IS_A, IMPLEMENTED_IN in seed
    assert rels & {"USED_FOR", "USES", "IS_A", "IMPLEMENTED_IN"}


@pytest.mark.asyncio
async def test_get_neighbors_not_found(repo: GraphRepository) -> None:
    results = await repo.get_neighbors("__ghost__")
    assert results == []


# ---------------------------------------------------------------------------
# Q5 — get_model_tasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_tasks_bert(repo: GraphRepository) -> None:
    result = await repo.get_model_tasks("BERT")
    assert result is not None
    assert result["model"] == "BERT"
    assert "Text Classification" in result["tasks"]
    assert "Question Answering" in result["tasks"]


@pytest.mark.asyncio
async def test_get_model_tasks_not_found(repo: GraphRepository) -> None:
    result = await repo.get_model_tasks("__ghost__")
    assert result is None


# ---------------------------------------------------------------------------
# Q6 — get_model_methods
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_methods_bert(repo: GraphRepository) -> None:
    result = await repo.get_model_methods("BERT")
    assert result is not None
    assert result["model"] == "BERT"
    assert "Fine-tuning" in result["methods"]
    assert "Masked Language Modeling" in result["methods"]


@pytest.mark.asyncio
async def test_get_model_methods_not_found(repo: GraphRepository) -> None:
    result = await repo.get_model_methods("__ghost__")
    assert result is None


# ---------------------------------------------------------------------------
# Q8 — compare_models
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_compare_models(repo: GraphRepository) -> None:
    result = await repo.compare_models("BERT", "GPT")
    assert result is not None
    assert result["model_a"] == "BERT"
    assert result["model_b"] == "GPT"
    assert isinstance(result["tasks_a"], list)
    assert isinstance(result["tasks_b"], list)
    assert isinstance(result["methods_a"], list)
    assert isinstance(result["methods_b"], list)


@pytest.mark.asyncio
async def test_compare_models_unknown(repo: GraphRepository) -> None:
    result = await repo.compare_models("__ghost_a__", "__ghost_b__")
    assert result is None


# ---------------------------------------------------------------------------
# Q9 — entity_exists
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_entity_exists_true(repo: GraphRepository) -> None:
    assert await repo.entity_exists("BERT") is True


@pytest.mark.asyncio
async def test_entity_exists_false(repo: GraphRepository) -> None:
    assert await repo.entity_exists("__nonexistent__") is False


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_sources(repo: GraphRepository) -> None:
    results = await repo.list_sources()
    sources = {r["source"] for r in results}

    assert "manual_seed" in sources
