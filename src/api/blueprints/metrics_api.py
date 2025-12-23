"""Prometheus metrics endpoint."""
from flask import Blueprint, Response
from src.monitoring.metrics import get_metrics
from src.api.auth import optional_api_key

metrics_api_bp = Blueprint("metrics_api", __name__, url_prefix="/api/metrics")


@metrics_api_bp.route("", methods=["GET"])
@optional_api_key
def metrics():
    """Prometheus metrics endpoint."""
    metrics_text = get_metrics()
    return Response(metrics_text, mimetype="text/plain")

