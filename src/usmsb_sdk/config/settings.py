"""
Configuration Management Module

Handles loading, validation, and management of SDK configuration
from environment variables, files, and programmatic sources.
"""

import os
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """LLM provider configuration."""
    provider: str = Field(default="openai", description="LLM provider name")
    api_key: str | None = Field(default=None, description="API key for the provider")
    model: str = Field(default="gpt-4-turbo-preview", description="Model name")
    embedding_model: str = Field(default="text-embedding-3-small", description="Embedding model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=4096, ge=1, description="Maximum tokens per request")
    timeout: float = Field(default=30.0, ge=1.0, description="Request timeout in seconds")


class DatabaseConfig(BaseSettings):
    """Database configuration."""
    url: str = Field(default="sqlite+aiosqlite:///./usmsb.db", description="Database URL")
    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    echo: bool = Field(default=False, description="Echo SQL statements")


class RedisConfig(BaseSettings):
    """Redis configuration."""
    url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    enabled: bool = Field(default=False, description="Enable Redis caching")


class APIConfig(BaseSettings):
    """API server configuration."""
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")
    api_key_header: str = Field(default="X-API-Key", description="API key header name")


class LoggingConfig(BaseSettings):
    """Logging configuration."""
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format (json or text)")
    file: str | None = Field(default=None, description="Log file path")


class Settings(BaseSettings):
    """
    Main SDK settings.

    Loads configuration from environment variables and .env files.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = Field(default="USMSB SDK", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment name")

    # Authentication / Security settings
    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET", description="JWT secret key")
    session_secret: str | None = Field(
        default=None, alias="SESSION_SECRET", description="Session secret"
    )
    nonce_expiry_seconds: int = Field(
        default=300, alias="NONCE_EXPIRY_SECONDS", description="Nonce expiry in seconds"
    )
    session_duration_hours: int = Field(
        default=168,
        alias="SESSION_DURATION_HOURS",
        description="Session duration in hours",
    )

    # CORS settings
    allowed_origins: str | None = Field(
        default=None, alias="ALLOWED_ORIGINS", description="Allowed CORS origins"
    )

    # Blockchain settings
    eth_rpc_url: str | None = Field(
        default=None, alias="ETH_RPC_URL", description="Ethereum RPC URL"
    )
    chain_id: int = Field(default=1, alias="CHAIN_ID", description="Blockchain chain ID")

    # Server settings (direct aliases for common env vars)
    host: str | None = Field(default=None, alias="HOST", description="Server host")
    port: int | None = Field(default=None, alias="PORT", description="Server port")
    debug: bool | None = Field(default=None, alias="DEBUG", description="Enable debug mode")

    # LLM configuration
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # OpenAI specific (for backward compatibility)
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-turbo-preview", alias="OPENAI_MODEL")

    # Google specific
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_model: str = Field(default="gemini-pro", alias="GEMINI_MODEL")

    # Database
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    database_url: str | None = Field(default=None, alias="DATABASE_URL")

    # Redis
    redis: RedisConfig = Field(default_factory=RedisConfig)
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    # API
    api: APIConfig = Field(default_factory=APIConfig)
    api_host: str | None = Field(default=None, alias="API_HOST")
    api_port: int | None = Field(default=None, alias="API_PORT")

    # Logging
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    log_level: str | None = Field(default=None, alias="LOG_LEVEL")

    @field_validator("llm", mode="before")
    @classmethod
    def set_llm_api_key(cls, v: Any, info) -> LLMConfig:
        """Set LLM API key from environment if not provided."""
        if isinstance(v, dict):
            if not v.get("api_key"):
                # Try OpenAI key first
                v["api_key"] = os.getenv("OPENAI_API_KEY")
            return LLMConfig(**v)
        return v

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Override with direct environment variables
        if self.openai_api_key and not self.llm.api_key:
            self.llm.api_key = self.openai_api_key
        if self.openai_model and self.llm.model == "gpt-4-turbo-preview":
            self.llm.model = self.openai_model

        if self.database_url:
            self.database.url = self.database_url
        if self.redis_url:
            self.redis.url = self.redis_url

        if self.api_host:
            self.api.host = self.api_host
        if self.api_port:
            self.api.port = self.api_port

        # Also apply direct host/port/debug settings
        if self.host:
            self.api.host = self.host
        if self.port:
            self.api.port = self.port
        if self.debug is not None:
            self.api.debug = self.debug

        if self.log_level:
            self.logging.level = self.log_level


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global _settings
    _settings = Settings()
    return _settings
