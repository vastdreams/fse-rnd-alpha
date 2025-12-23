"""Flask app factory."""
from flask import Flask
from config.settings import get_settings
from src.api.extensions import init_extensions
from src.api.middleware.error_handler import register_error_handlers
from src.api.blueprints.health_api import health_api_bp
from src.api.blueprints.factor_api import factor_api_bp
from src.api.blueprints.backtest_api import backtest_api_bp
from src.api.blueprints.company_api import company_api_bp
from src.api.blueprints.unified_api import unified_api_bp
from src.api.blueprints.metrics_api import metrics_api_bp
from src.api.schemas.openapi_spec import openapi_bp
from src.logging.logger import get_logger
from src.monitoring.sentry_config import init_sentry

logger = get_logger(__name__)
settings = get_settings()


def create_flask_app() -> Flask:
    """Create and configure Flask application."""
    # Initialize Sentry before creating app
    init_sentry()
    
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    
    # Initialize extensions
    init_extensions(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    app.register_blueprint(health_api_bp)
    app.register_blueprint(factor_api_bp)
    app.register_blueprint(backtest_api_bp)
    app.register_blueprint(company_api_bp)
    app.register_blueprint(unified_api_bp)
    app.register_blueprint(metrics_api_bp)
    app.register_blueprint(openapi_bp)
    
    # Initialize database connection
    from src.db.connection import init_engine
    init_engine()
    
    # Initialize Redis cache if enabled
    if settings.REDIS_ENABLED and settings.REDIS_URL:
        from src.ai.utils.gpt_cache import initialize_redis_cache
        try:
            initialize_redis_cache(settings.REDIS_URL)
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis cache: {e}")
    
    logger.info("Flask app created with blueprints, error handlers, and monitoring.")
    return app
