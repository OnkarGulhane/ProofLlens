"""Central application configuration using Pydantic Settings."""

import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment variable definitions."""

    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General Project Information
    PROJECT_NAME: str = "ProofLens AI"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    API_V1_STR: str = "/api/v1"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/prooflens_db"
    DATABASE_ECHO: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if v:
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Local Storage
    STORAGE_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB

    # AI Configuration
    LLM_PROVIDER: str = "gemini"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    SIMILARITY_THRESHOLD_DEFAULT: float = 0.65
    TOP_K_DEFAULT: int = 5

    # Google Gemini Configuration
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"


settings = Settings()
