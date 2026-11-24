import httpx
import pytest
from fastapi.testclient import TestClient
from app.core.exceptions import Neo4jConnectionError
from app.main import app
from app.schemas.query import QueryServiceResult, QueryType
from app.services.query_service import get_query_service
from app.services.llm_client import GeminiLLMClient, LLMClientError


class QueryStub:
    async def answer(self, text, language):
        return QueryServiceResult(answer='ok', query_type=QueryType.DEFINITION, source_entities=[], from_kb=False)


@pytest.mark.parametrize('body,status', [
    ({'text': '', 'language': 'en'}, 422),
    ({'text': 'a' * 500, 'language': 'en'}, 200),
    ({'text': 'a' * 501, 'language': 'en'}, 422),
    ({'text': 'BERT', 'language': 'de'}, 422),
    ({'text': None}, 422),
])
def test_query_request_boundaries(body, status):
    app.dependency_overrides[get_query_service] = lambda: QueryStub()
    try:
        with TestClient(app) as client:
            assert client.post('/query', json=body).status_code == status
    finally:
        app.dependency_overrides.clear()


def test_neo4j_service_error_maps_to_503():
    class BrokenQuery:
        async def answer(self, text, language):
            raise Neo4jConnectionError('database unavailable')
    app.dependency_overrides[get_query_service] = lambda: BrokenQuery()
    try:
        with TestClient(app) as client:
            response = client.post('/query', json={'text': 'BERT'})
        assert response.status_code == 503
        assert response.json()['title'] == 'Neo4j Connection Error'
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize('exception_type', [httpx.ConnectError, httpx.ReadTimeout])
async def test_gemini_network_failures_exhaust_retries(exception_type):
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        raise exception_type('unavailable', request=request)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GeminiLLMClient(api_key='test', model='test', max_retries=2, retry_delay_seconds=0, client=http)
        with pytest.raises(LLMClientError):
            await client.generate('test')
    assert calls == 3


async def test_gemini_rate_limit_exhausts_retries():
    calls = 0
    async def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(429, json={'error': 'quota exceeded'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = GeminiLLMClient(api_key='test', model='test', max_retries=1, retry_delay_seconds=0, client=http)
        with pytest.raises(LLMClientError):
            await client.generate('test')
    assert calls == 2
