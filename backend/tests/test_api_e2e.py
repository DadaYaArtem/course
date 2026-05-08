from fastapi.testclient import TestClient

from app.main import app
from app.schemas.llm import LLMGenerationResult
from app.services.llm_client import get_llm_client


class RecordingLLMClient:
    """LLM test double for API e2e tests."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Record prompt and return a deterministic answer."""
        self.prompts.append(prompt)
        return LLMGenerationResult(
            text="Mocked API answer",
            latency_ms=1.0,
            model="mock-llm",
        )


def test_query_endpoint_e2e_real_service_real_neo4j_mocked_llm() -> None:
    """POST /query runs the real service stack with only the LLM mocked."""
    llm_client = RecordingLLMClient()
    app.dependency_overrides[get_llm_client] = lambda: llm_client
    try:
        with TestClient(app) as client:
            response = client.post(
                "/query",
                json={"text": "What is BERT used for?", "language": "en"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Mocked API answer",
        "query_type": "capabilities",
        "source_entities": ["BERT"],
        "from_kb": True,
    }
    assert "Question Answering" in llm_client.prompts[0]


def test_documents_endpoint_e2e_lists_real_neo4j_sources() -> None:
    """GET /documents uses the real repository and returns indexed sources."""
    with TestClient(app) as client:
        response = client.get("/documents")

    assert response.status_code == 200
    sources = {item["source"] for item in response.json()}
    assert "manual_seed" in sources
