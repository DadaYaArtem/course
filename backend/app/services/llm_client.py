import asyncio
import time
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.core.exceptions import LLMError
from app.schemas.llm import LLMGenerationResult


class LLMClientError(LLMError):
    """Raised when an LLM request fails or returns an invalid response."""


class GeminiLLMClient:
    """Async Gemini REST client for text generation."""

    _RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        retry_delay_seconds: float = 0.25,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the Gemini client.

        Args:
            api_key: Gemini API key. Defaults to application settings.
            model: Gemini model name. Defaults to application settings.
            base_url: Gemini API base URL. Defaults to application settings.
            timeout_seconds: Request timeout in seconds.
            max_retries: Number of retries for transient failures.
            retry_delay_seconds: Base delay between retry attempts.
            client: Optional injected AsyncClient, mainly for tests.
        """
        settings = self._load_settings()
        self._api_key = api_key or settings.gemini_api_key
        self._model = model or settings.gemini_model
        self._base_url = (base_url or settings.gemini_base_url).rstrip("/")
        self._timeout_seconds = timeout_seconds or settings.llm_timeout_seconds
        self._max_retries = (
            settings.llm_max_retries if max_retries is None else max_retries
        )
        self._retry_delay_seconds = retry_delay_seconds
        self._client = client
        self._owns_client = client is None

    async def __aenter__(self) -> "GeminiLLMClient":
        """Return the initialized client for async context manager use."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: Any,
    ) -> None:
        """Close the owned HTTP client when leaving a context manager."""
        await self.close()

    async def generate(self, prompt: str) -> LLMGenerationResult:
        """Generate text from a prompt.

        Args:
            prompt: Prompt prepared by the prompt builder.

        Returns:
            Generated text, latency, and model metadata.

        Raises:
            LLMClientError: If the request fails or response has no text.
        """
        started_at = time.perf_counter()
        response_json = await self._post_with_retries(prompt)
        text = self._extract_text(response_json)
        latency_ms = (time.perf_counter() - started_at) * 1000
        return LLMGenerationResult(
            text=text,
            latency_ms=latency_ms,
            model=self._model,
        )

    async def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def _post_with_retries(self, prompt: str) -> dict[str, Any]:
        """Send a Gemini request and retry transient failures."""
        last_error: Exception | None = None
        attempts = self._max_retries + 1

        for attempt in range(attempts):
            try:
                response = await self._get_client().post(
                    self._generate_url(),
                    headers=self._headers(),
                    json=self._payload(prompt),
                    timeout=self._timeout_seconds,
                )
                if self._should_retry_response(response) and attempt < attempts - 1:
                    await self._sleep_before_retry(attempt)
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt >= attempts - 1:
                    break
                await self._sleep_before_retry(attempt)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if not self._is_retryable_status(exc.response.status_code):
                    break
                if attempt >= attempts - 1:
                    break
                await self._sleep_before_retry(attempt)

        raise LLMClientError("Gemini generation request failed") from last_error

    def _extract_text(self, response_json: dict[str, Any]) -> str:
        """Extract generated text from a Gemini generateContent response."""
        text_parts: list[str] = []
        candidates = response_json.get("candidates", [])
        for candidate in candidates:
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            for part in parts:
                text = part.get("text")
                if text:
                    text_parts.append(text)

        text = "".join(text_parts).strip()
        if not text:
            raise LLMClientError("Gemini response did not contain generated text")
        return text

    def _get_client(self) -> httpx.AsyncClient:
        """Return the active AsyncClient, creating one on demand."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    def _generate_url(self) -> str:
        """Return the Gemini generateContent URL for the configured model."""
        return f"{self._base_url}/models/{self._model}:generateContent"

    def _headers(self) -> dict[str, str]:
        """Return Gemini request headers."""
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

    def _payload(self, prompt: str) -> dict[str, Any]:
        """Return Gemini generateContent request payload."""
        return {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt,
                        }
                    ],
                }
            ]
        }

    def _should_retry_response(self, response: httpx.Response) -> bool:
        """Return whether an HTTP response should be retried."""
        return self._is_retryable_status(response.status_code)

    def _is_retryable_status(self, status_code: int) -> bool:
        """Return whether an HTTP status code is retryable."""
        return status_code in self._RETRYABLE_STATUS_CODES

    async def _sleep_before_retry(self, attempt: int) -> None:
        """Sleep before retrying with exponential backoff."""
        delay = self._retry_delay_seconds * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)

    def _load_settings(self) -> Any:
        """Load application settings lazily to keep tests injectable."""
        from app.core.config import settings

        return settings


async def generate_text(prompt: str) -> LLMGenerationResult:
    """Generate text with the default Gemini client.

    Args:
        prompt: Prompt prepared by the prompt builder.

    Returns:
        Generated text, latency, and model metadata.
    """
    async with GeminiLLMClient() as client:
        return await client.generate(prompt)


async def get_llm_client() -> AsyncGenerator[GeminiLLMClient, None]:
    """FastAPI dependency that injects an LLM client."""
    async with GeminiLLMClient() as client:
        yield client
