"""
ContextBridge Backend — Application Settings
Validates all required environment variables at startup using Pydantic Settings.
Missing required variables cause an immediate startup failure with a descriptive error.
"""

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
    # Database
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string (asyncpg format). "
        "Example: postgresql+asyncpg://user:pass@localhost:5432/contextbridge",
    )

    # -------------------------------------------------------------------------
    # Auth0
    # -------------------------------------------------------------------------
    AUTH0_DOMAIN: str = Field(
        ...,
        description="Auth0 tenant domain. Example: your-tenant.us.auth0.com",
    )
    AUTH0_AUDIENCE: str = Field(
        ...,
        description="Auth0 API audience identifier.",
    )

    # -------------------------------------------------------------------------
    # Stripe
    # -------------------------------------------------------------------------
    STRIPE_SECRET_KEY: str = Field(
        ...,
        description="Stripe secret API key.",
    )
    STRIPE_WEBHOOK_SECRET: str = Field(
        ...,
        description="Stripe webhook signing secret for payload verification.",
    )

    # -------------------------------------------------------------------------
    # LLM Providers
    # -------------------------------------------------------------------------
    OPENAI_API_KEY: str = Field(
        ...,
        description="OpenAI API key for summarization and embeddings.",
    )
    ANTHROPIC_API_KEY: str = Field(
        ...,
        description="Anthropic API key for Claude summarization preset.",
    )

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for summarization cache.",
    )

    # -------------------------------------------------------------------------
    # Sentry
    # -------------------------------------------------------------------------
    SENTRY_DSN: str | None = Field(
        default=None,
        description="Sentry DSN for error collection. Optional.",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_ENV: str = Field(
        default="development",
        description="Application environment: development | staging | production",
    )
    CORS_ORIGINS: list[str] = Field(
        default=["chrome-extension://*"],
        description="Allowed CORS origins.",
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Application log level.",
    )


settings = Settings()  # type: ignore[call-arg]
