"""Sentry error tracking configuration."""
import os
import logging
from config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def init_sentry():
    """Initialize Sentry error tracking."""
    sentry_dsn = os.getenv("SENTRY_DSN") or settings.SENTRY_DSN
    
    if not sentry_dsn:
        return None
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.ENV,
            integrations=[
                FlaskIntegration(),
                SqlalchemyIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1 if settings.ENV == "production" else 1.0,
            profiles_sample_rate=0.1 if settings.ENV == "production" else 1.0,
            send_default_pii=False,  # Don't send PII
        )
        
        logger.info("Sentry initialized successfully")
        return sentry_sdk
    except ImportError:
        # Sentry not installed, skip
        logger.debug("Sentry SDK not installed, skipping initialization")
        return None
    except Exception as e:
        # Sentry initialization failed, log but don't crash
        logger.warning(f"Failed to initialize Sentry: {e}")
        return None

