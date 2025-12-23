"""Health check API endpoints."""
from flask import Blueprint, jsonify
from src.db.connection import check_database_health
from src.logging.logger import get_logger

logger = get_logger(__name__)
health_api_bp = Blueprint("health_api", __name__)


@health_api_bp.route("/health", methods=["GET"])
def health():
    """Basic health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@health_api_bp.route("/health/detailed", methods=["GET"])
def detailed_health():
    """Detailed health check with dependency status."""
    db_health = check_database_health()
    
    health_status = {
        "status": "healthy" if db_health.get("status") == "healthy" else "degraded",
        "timestamp": db_health.get("timestamp"),
        "dependencies": {
            "database": db_health
        }
    }
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return jsonify(health_status), status_code
