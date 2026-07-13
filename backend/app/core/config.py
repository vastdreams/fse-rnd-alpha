"""
PATH: backend/app/core/config.py
PURPOSE:
  - Application configuration via pydantic-settings
  - Environment variable loading

ROLE IN ARCHITECTURE:
  - Configuration layer
"""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Database (asyncpg for async SQLAlchemy)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rd_alpha"
    DATABASE_ECHO: bool = False
    
    @property
    def async_database_url(self) -> str:
        """Ensure DATABASE_URL uses asyncpg driver."""
        url = self.DATABASE_URL
        # Convert psycopg2 to asyncpg if needed
        if "postgresql://" in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://")
        if "+psycopg2" in url:
            url = url.replace("+psycopg2", "+asyncpg")
        return url
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # S3
    S3_BUCKET: str = "fse-rnd-alpha-data"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    
    # SEC API
    SEC_USER_AGENT: str = "FSE Research contact@example.com"
    SEC_RATE_LIMIT: int = 10  # requests per second
    
    # FMP API (Financial Modeling Prep)
    FMP_API_KEY: str = ""

    # SaaS AI Repricing study data sources (own-the-data layer)
    ALPHAVANTAGE_API_KEY: str = ""        # Alpha Vantage Premium: transcripts, fundamentals, listing status
    NASDAQ_DATA_LINK_API_KEY: str = ""    # Nasdaq Data Link / Sharadar Core US Equities bundle
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:80", 
        "http://localhost",
        "https://research.finsoeasy.com",
        "http://research.finsoeasy.com",
    ]
    
    # Security
    SECRET_KEY: str = "change-me-in-production-use-secrets-token-hex-32"
    API_KEY_REQUIRED: bool = False
    ADMIN_CLIENTS_CONFIG_PATH: str = ""  # Optional path to admin_clients.json (do not commit secrets)
    # Public investor-platform account lifecycle.
    AUTH_USERS_PATH: str = ""
    AUTH_PUBLIC_REGISTRATION: bool = True
    AUTH_REQUIRE_EMAIL_VERIFICATION: bool = True
    AUTH_EMAIL_FROM: str = ""
    AUTH_RESET_URL: str = "https://research.finsoeasy.com/reset-password"
    AUTH_VERIFY_URL: str = "https://research.finsoeasy.com/verify-email"
    AUTH_VERIFICATION_TTL_MINUTES: int = 60 * 24
    AUTH_RESET_TTL_MINUTES: int = 60
    AUTH_SEED_ROLE: str = "user"
    AUTH_SECONDARY_SEED_ROLE: str = "user"
    RESEND_API_KEY: str = ""
    
    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_SUCCESS_URL: str = "https://research.finsoeasy.com/donate/success"
    STRIPE_CANCEL_URL: str = "https://research.finsoeasy.com/donate"
    
    # Server
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra env vars from legacy config


_INSECURE_SECRET_KEYS = {
    "",
    "change-me-in-production-use-secrets-token-hex-32",
    "change-in-production",
    "test-secret-key",
}


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    s = Settings()
    # Fail closed: JWTs signed with defaults or a short key are forgeable.
    # Development can explicitly opt into a test key with DEBUG=true.
    if not s.DEBUG and (
        s.SECRET_KEY in _INSECURE_SECRET_KEYS or len(s.SECRET_KEY) < 32
    ):
        raise RuntimeError(
            "SECRET_KEY must be a non-default value of at least 32 characters "
            "(e.g. `python -c 'import secrets; print(secrets.token_hex(32))'`) "
            "or run with DEBUG=true for local development."
        )
    return s


settings = get_settings()
