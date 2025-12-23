"""Run production server with Gunicorn."""
# Setup path - must be first
import _setup_path  # noqa: F401

import os
import socket
from config.settings import get_settings
from src.logging.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def is_port_available(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is available."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
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
    # Check port availability
    requested_port = settings.SERVER_PORT
    port = requested_port
    if not is_port_available(requested_port):
        logger.warning(f"Port {requested_port} is already in use. Searching for alternative...")
        try:
            available_port = find_available_port(requested_port + 1)
            logger.info(f"Using port {available_port} instead of requested {requested_port}")
            port = available_port
        except RuntimeError as e:
            logger.error(f"Failed to find an available port: {e}")
            exit(1)
    else:
        logger.info(f"Requested port {port} is available.")
    
    # Determine number of workers
    workers = int(os.getenv("GUNICORN_WORKERS", "4"))
    threads = int(os.getenv("GUNICORN_THREADS", "2"))
    timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
    
    logger.info(f"Starting production server on port {port} with {workers} workers")
    
    # Import and run with gunicorn
    import gunicorn.app.base
    
    from src.api.app_factory import create_flask_app
    
    class StandaloneApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()
        
        def load_config(self):
            for key, value in self.options.items():
                self.cfg.set(key.lower(), value)
        
        def load(self):
            return self.application
    
    options = {
        "bind": f"0.0.0.0:{port}",
        "workers": workers,
        "threads": threads,
        "timeout": timeout,
        "worker_class": "sync",
        "accesslog": "-",
        "errorlog": "-",
        "loglevel": "info",
        "preload_app": True,
    }
    
    app = create_flask_app()
    StandaloneApplication(app, options).run()

