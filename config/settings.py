# =============================================================================
# File: config/settings.py
# =============================================================================
# Purpose:
#   Central configuration using Pydantic BaseSettings.
#
# First principles:
#   - One place to pull ENV + defaults.
#   - Avoid sprinkling os.getenv() everywhere.
# =============================================================================

from pydantic import Field

# Try to use pydantic-settings (Pydantic v2), fallback to pydantic BaseSettings
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for older pydantic versions
    try:
        from pydantic import BaseSettings
    except ImportError:
        raise ImportError("pydantic or pydantic-settings is required")


class Settings(BaseSettings):
    ENV: str = Field(default="development", description="Flask environment name.")
    DEBUG: bool = Field(default=True, description="Enable Flask debug mode?")
    SECRET_KEY: str = Field(default="change-me", description="Flask secret key.")
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://user:password@localhost:5432/research_rnd_alpha",
        description="SQLAlchemy DB URL.",
    )
    OPENAI_API_KEY: str = Field(
        default="",
        description="OpenAI API key for GPT models."
    )
    SEC_USER_AGENT: str = Field(
        default="Research Bot (research@example.com)",
        description="User-Agent header for SEC API requests."
    )
    GPT_MODEL: str = Field(
        default="gpt-5.1",
        description="GPT model to use (gpt-5.1, gpt-5, gpt-4o, gpt-4-turbo, etc.). Default: gpt-5.1 (latest)."
    )
    PILOT_MAX_COMPANIES: int = Field(
        default=10,
        description="Maximum number of companies for pilot testing."
    )
    SERVER_PORT: int = Field(
        default=8055,
        description="Port number for Flask/Dash server."
    )
    REDIS_URL: str = Field(
        default="",
        description="Redis URL for caching (optional, e.g., redis://localhost:6379/0)."
    )
    REDIS_ENABLED: bool = Field(
        default=False,
        description="Enable Redis caching for GPT API responses."
    )
    SENTRY_DSN: str = Field(
        default="",
        description="Sentry DSN for error tracking (optional)."
    )
    REQUIRE_AUTH: bool = Field(
        default=False,
        description="Require API key authentication (set to true in production)."
    )
    API_KEYS: str = Field(
        default="",
        description="Comma-separated list of valid API keys."
    )
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."
    )
    USE_JSON_LOGGING: bool = Field(
        default=False,
        description="Use JSON structured logging (recommended for production)."
    )

    # Pydantic v1 syntax (works for both v1 and v2 with pydantic-settings)
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env


_settings_instance: Settings = None


def get_settings() -> Settings:
    """
    Get the global Settings instance (singleton pattern).
    
    Returns:
        Settings instance loaded from environment variables and .env file
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
