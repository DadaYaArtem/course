from enum import StrEnum

from pydantic import BaseModel, Field


class QueryType(StrEnum):
    """Supported user query intents."""

    DEFINITION = "definition"
    COMPARISON = "comparison"
    CAPABILITIES = "capabilities"
    METHODS = "methods"
    RECOMMENDATION = "recommendation"
    UNKNOWN = "unknown"


class ClassificationResult(BaseModel):
    """Result of user query classification."""

    query_type: QueryType
    entities: list[str] = Field(default_factory=list)
    classification_source: str = "rules"



class PromptBuildResult(BaseModel):
    """Prompt text prepared for an LLM call."""

    prompt: str
    warning: bool = False


class QueryServiceResult(BaseModel):
    """Structured result returned by the query orchestration service."""

    answer: str
    source_entities: list[str] = Field(default_factory=list)
    query_type: QueryType
    from_kb: bool
    classification_source: str | None = None