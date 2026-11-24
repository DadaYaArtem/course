from pydantic import PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str = "neo4j"

    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    query_classifier_use_llm: bool = False

    document_upload_dir: str = "uploads/documents"
    document_parser_enabled: bool = False
    document_job_timeout_seconds: PositiveInt = 120
    document_job_max_attempts: PositiveInt = 3
    document_job_max_bytes: PositiveInt = 25 * 1024 * 1024
    parser_service_dir: str = "../neo4j/parser_service"
    parser_output_dir: str = "parser/output"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
