"""Flask extensions initialization."""
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config.settings import get_settings
from src.logging.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Initialize limiter (will be configured in init_extensions)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use Redis in production: settings.REDIS_URL
)


def init_extensions(app):
    """Initialize Flask extensions."""
    # CORS configuration
    CORS(app, resources={
        r"/api/*": {
            "origins": "*" if settings.DEBUG else ["https://yourdomain.com"],
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Rate limiting
    # Use Redis if available, otherwise memory
    storage_uri = settings.REDIS_URL if settings.REDIS_ENABLED and settings.REDIS_URL else "memory://"
    limiter.storage_uri = storage_uri
    limiter.init_app(app)
    
    logger.info(f"Flask extensions initialized: CORS, Rate Limiting (storage: {storage_uri})")
