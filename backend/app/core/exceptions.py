from http import HTTPStatus


class AppError(Exception):
    """Base application exception rendered as RFC 7807 Problem Details."""

    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    title = "Internal Server Error"
    type_uri = "about:blank"

    def __init__(
        self,
        detail: str | None = None,
        status_code: int | None = None,
        title: str | None = None,
        type_uri: str | None = None,
    ) -> None:
        """Initialize an application error.

        Args:
            detail: Human-readable error detail.
            status_code: Optional HTTP status override.
            title: Optional problem title override.
            type_uri: Optional problem type URI override.
        """
        self.detail = detail or self.title
        self.status_code = status_code or int(self.status_code)
        self.title = title or self.title
        self.type_uri = type_uri or self.type_uri
        super().__init__(self.detail)


class EntityNotFoundError(AppError):
    """Raised when a requested graph entity cannot be found."""

    status_code = HTTPStatus.NOT_FOUND
    title = "Entity Not Found"
    type_uri = "https://example.com/problems/entity-not-found"


class Neo4jConnectionError(AppError):
    """Raised when Neo4j access fails."""

    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    title = "Neo4j Connection Error"
    type_uri = "https://example.com/problems/neo4j-connection-error"


class LLMError(AppError):
    """Raised when LLM generation fails."""

    status_code = HTTPStatus.BAD_GATEWAY
    title = "LLM Error"
    type_uri = "https://example.com/problems/llm-error"


class DocumentServiceError(AppError):
    """Raised when document handling fails."""

    status_code = HTTPStatus.BAD_REQUEST
    title = "Document Error"
    type_uri = "https://example.com/problems/document-error"
