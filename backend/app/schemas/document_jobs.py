from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DocumentJob(BaseModel):
    id: UUID
    filename: str
    status: Literal["queued", "running", "completed", "failed"]
    attempts: int
    max_attempts: int
    created_at: str
    updated_at: str
    error: str | None
