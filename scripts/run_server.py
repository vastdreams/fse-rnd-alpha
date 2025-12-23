"""Run Flask + Dash server."""
# Setup path - must be first
import _setup_path  # noqa: F401

import socket
from src.api.app_factory import create_flask_app
from src.user_dash.app import create_user_dash
from config.settings import get_settings
from src.logging.logger import get_logger

logger = get_logger(__name__)


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            result = s.bind((host, port))
            return True
    except OSError:
        return False


def find_available_port(start_port: int, max_attempts: int = 10) -> int:
    """Find an available port starting from start_port."""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(port):
            return port
    raise RuntimeError(f"Could not find an available port starting from {start_port}")


if __name__ == "__main__":
    settings = get_settings()
    
    # Check port availability
    requested_port = settings.SERVER_PORT
    if not is_port_available(requested_port):
        logger.warning(f"Port {requested_port} is already in use. Searching for alternative...")
        available_port = find_available_port(requested_port)
        logger.warning(f"⚠️  Port {requested_port} was in use. Using port {available_port} instead.")
        logger.info(f"Server will be available at: http://localhost:{available_port}")
        port = available_port
    else:
        port = requested_port
        logger.info(f"✓ Port {port} is available")
        logger.info(f"Server will be available at: http://localhost:{port}")
    
    # Create Flask app
    flask_app = create_flask_app()
    
    # Create Dash app
    dash_app = create_user_dash(server=flask_app)
    
    # Run server
    logger.info(f"=" * 60)
    logger.info(f"Starting R&D Alpha Server")
    logger.info(f"URL: http://localhost:{port}")
    logger.info(f"URL: http://0.0.0.0:{port}")
    logger.info(f"=" * 60)
    dash_app.run(debug=settings.DEBUG, host="0.0.0.0", port=port)

