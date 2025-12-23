"""Error handling middleware for Flask API."""
from flask import jsonify, request
from src.logging.logger import get_logger
from src.utils.exceptions import ApiError, ValidationError
import traceback

logger = get_logger(__name__)


def register_error_handlers(app):
    """Register error handlers for the Flask app."""
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Handle validation errors."""
        logger.warning(f"Validation error: {e}", extra={"path": request.path})
        return jsonify({
            "error": "Validation Error",
            "message": str(e),
            "type": "validation_error"
        }), 400
    
    @app.errorhandler(ApiError)
    def handle_api_error(e):
        """Handle API errors."""
        logger.error(f"API error: {e}", extra={"path": request.path})
        return jsonify({
            "error": "API Error",
            "message": str(e),
            "type": "api_error"
        }), 500
    
    @app.errorhandler(404)
    def handle_not_found(e):
        """Handle 404 errors."""
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": request.path
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        """Handle internal server errors."""
        logger.error(f"Internal server error: {e}\n{traceback.format_exc()}", extra={"path": request.path})
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": "internal_error"
        }), 500
    
    @app.errorhandler(Exception)
    def handle_generic_error(e):
        """Handle all other exceptions."""
        logger.error(f"Unhandled exception: {e}\n{traceback.format_exc()}", extra={"path": request.path})
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": "unhandled_exception"
        }), 500

