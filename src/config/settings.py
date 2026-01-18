"""
Application Settings

This module defines application settings using Pydantic Settings,
with support for environment variables and configuration files.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings.

    Settings are loaded from environment variables with fallback to
    default values. Environment variables should be prefixed with
    QINGYU_AI_ (e.g., QINGYU_AI_PORT=8000).
    """

    model_config = SettingsConfigDict(
        env_prefix="QINGYU_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # =============================================================================
    # Application Settings
    # =============================================================================

    app_name: str = Field(default="Qingyu AI Service", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment name")

    # =============================================================================
    # Server Settings
    # =============================================================================

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    workers: int = Field(default=1, ge=1, description="Number of worker processes")
    reload: bool = Field(default=False, description="Enable auto-reload")

    # =============================================================================
    # API Settings
    # =============================================================================

    api_prefix: str = Field(default="/api/v1", description="API prefix")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="CORS allow credentials")
    cors_allow_methods: list[str] = Field(
        default=["*"],
        description="CORS allowed methods"
    )
    cors_allow_headers: list[str] = Field(
        default=["*"],
        description="CORS allowed headers"
    )

    # =============================================================================
    # LLM Settings
    # =============================================================================

    llm_provider: str = Field(default="openai", description="LLM provider")
    llm_model: str = Field(default="gpt-4", description="Default LLM model")
    llm_temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Default temperature")
    llm_max_tokens: int = Field(default=2000, ge=1, description="Default max tokens")
    llm_api_key: Optional[str] = Field(default=None, description="LLM API key")

    # =============================================================================
    # LangChain Settings
    # =============================================================================

    langchain_api_key: Optional[str] = Field(default=None, description="LangChain API key")
    langchain_project: Optional[str] = Field(default=None, description="LangChain project name")
    langchain_tracing_v2: bool = Field(default=False, description="Enable LangChain tracing")

    # =============================================================================
    # Vector Database Settings
    # =============================================================================

    vector_db_host: str = Field(default="localhost", description="Vector database host")
    vector_db_port: int = Field(default=19530, ge=1, le=65535, description="Vector database port")
    vector_db_index_name: str = Field(default="qingyu", description="Default index name")

    # =============================================================================
    # Redis Settings
    # =============================================================================

    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, description="Redis database number")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # =============================================================================
    # Memory Settings
    # =============================================================================

    memory_max_entries: int = Field(default=10000, ge=1, description="Max memory entries")
    memory_ttl_seconds: int = Field(default=86400, ge=0, description="Memory TTL in seconds")
    memory_enable_embeddings: bool = Field(default=False, description="Enable embeddings")

    # =============================================================================
    # Logging Settings
    # =============================================================================

    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json or text)")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # =============================================================================
    # gRPC Settings
    # =============================================================================

    grpc_port: int = Field(default=50051, ge=1, le=65535, description="gRPC server port")
    grpc_max_workers: int = Field(default=10, ge=1, description="gRPC max workers")

    # =============================================================================
    # Security Settings
    # =============================================================================

    secret_key: str = Field(default="change-me-in-production", description="Secret key")
    access_token_expire_minutes: int = Field(default=30, ge=1, description="Access token expiration")

    # =============================================================================
    # Validators
    # =============================================================================

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "testing", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v.lower()


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This function caches the settings instance to avoid reloading
    from environment variables on every call.

    Returns:
        Settings: Application settings
    """
    return Settings()
