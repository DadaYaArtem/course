from fastapi import APIRouter, Depends

from app.schemas.ask import AskRequest, AskResponse
from app.services.query_service import QueryService, get_query_service

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=AskResponse, response_model_exclude_none=True)
async def query(
    request: AskRequest,
    service: QueryService = Depends(get_query_service),
) -> AskResponse:
    """Answer a user question through the query service."""
    result = await service.answer(request.text, request.language)
    return AskResponse(
        answer=result.answer,
        query_type=result.query_type,
        source_entities=result.source_entities,
        from_kb=result.from_kb,
        classification_source=result.classification_source,
    )
