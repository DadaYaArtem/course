import json

import httpx
import pytest

from app.services.llm_client import GeminiLLMClient, LLMClientError


def _json_response(status_code: int, body: dict) -> httpx.Response:
    """Return a JSON response for MockTransport handlers."""
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


@pytest.mark.asyncio
async def test_generate_returns_text_and_latency() -> None:
    """Client sends Gemini payload and returns generated text."""

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models/gemini-test:generateContent"
        assert request.headers["x-goog-api-key"] == "test-key"
        payload = json.loads(request.content)
        assert payload["contents"][0]["parts"][0]["text"] == "Prompt"
        return _json_response(
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {
                                    "text": "Generated answer",
                                }
                            ]
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url="https://generativelanguage.googleapis.com",
    ) as http_client:
        client = GeminiLLMClient(
            api_key="test-key",
            model="gemini-test",
            base_url="https://generativelanguage.googleapis.com/v1beta",
            max_retries=0,
            client=http_client,
        )

        result = await client.generate("Prompt")

    assert result.text == "Generated answer"
    assert result.model == "gemini-test"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_generate_combines_multiple_text_parts() -> None:
    """Client combines all text parts from the Gemini response."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(
            200,
            {
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"text": "Part one. "},
                                {"text": "Part two."},
                            ]
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = GeminiLLMClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=0,
            client=http_client,
        )

        result = await client.generate("Prompt")

    assert result.text == "Part one. Part two."


@pytest.mark.asyncio
async def test_generate_retries_transient_http_error() -> None:
    """Client retries retryable HTTP responses."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _json_response(503, {"error": {"message": "busy"}})
        return _json_response(
            200,
            {"candidates": [{"content": {"parts": [{"text": "Recovered"}]}}]},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = GeminiLLMClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=1,
            retry_delay_seconds=0,
            client=http_client,
        )

        result = await client.generate("Prompt")

    assert result.text == "Recovered"
    assert calls == 2


@pytest.mark.asyncio
async def test_generate_does_not_retry_client_error() -> None:
    """Client does not retry non-retryable HTTP responses."""
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _json_response(400, {"error": {"message": "bad request"}})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = GeminiLLMClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=2,
            retry_delay_seconds=0,
            client=http_client,
        )

        with pytest.raises(LLMClientError):
            await client.generate("Prompt")

    assert calls == 1


@pytest.mark.asyncio
async def test_generate_raises_when_response_has_no_text() -> None:
    """Client raises when Gemini response has no generated text."""

    async def handler(request: httpx.Request) -> httpx.Response:
        return _json_response(200, {"candidates": [{"content": {"parts": []}}]})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
    ) as http_client:
        client = GeminiLLMClient(
            api_key="test-key",
            model="gemini-test",
            max_retries=0,
            client=http_client,
        )

        with pytest.raises(LLMClientError):
            await client.generate("Prompt")
