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


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
