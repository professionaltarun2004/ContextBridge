"""
ContextOS Backend — Application Settings
All credentials loaded from environment variables.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Neo4j AuraDB
    # -------------------------------------------------------------------------
    NEO4J_URI: str = Field(..., description="Bolt URI for Neo4j AuraDB instance.")
    NEO4J_USERNAME: str = Field(default="neo4j", description="Neo4j auth username.")
    NEO4J_PASSWORD: str = Field(..., description="Neo4j auth password.")

    # -------------------------------------------------------------------------
    # LLM Providers (via LiteLLM)
    # -------------------------------------------------------------------------
    OPENAI_API_KEY: str = Field(default="sk-dummy", description="OpenAI API key.")
    GEMINI_API_KEY: str = Field(default="dummy", description="Google Gemini API key.")
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key.")

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_ENV: str = Field(default="development")
    MOCK_MODE: bool = Field(
        default=False,
        description="When True, bypasses live LLM and Neo4j calls for demo presentations.",
    )
    CORS_ORIGINS: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins.",
    )
    LOG_LEVEL: str = Field(default="INFO")


settings = Settings()  # type: ignore[call-arg]
