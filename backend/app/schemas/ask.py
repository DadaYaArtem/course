from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.query import QueryType

Language = Literal["ru", "en"]


class AskRequest(BaseModel):
    """Incoming question from the frontend."""

    text: str = Field(..., min_length=1, max_length=500, examples=["Что такое Transformer?"])
    language: Language = Field(default="ru")


class AskResponse(BaseModel):
    """Answer returned to the frontend."""

    answer: str
    query_type: QueryType
    source_entities: list[str]
    from_kb: bool
    classification_source: str | None = None
