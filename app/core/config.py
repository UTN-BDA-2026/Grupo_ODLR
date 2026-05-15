"""Application configuration.

Follows 12-Factor App: Configuration via environment variables.
"""

from typing import List, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Loads configuration from environment variables.
    Follows Single Responsibility Principle.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "PDF Extract API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_ALGORITHM: Literal["HS256"] = "HS256"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "pdf_extract_db"

    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]

    # Logging
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"  # text for dev, json for prod
    LOG_CORRELATION_ID: bool = True

    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://localhost:8000"]


settings = Settings()
