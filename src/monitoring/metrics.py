"""Prometheus metrics for monitoring."""
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Create dummy classes if prometheus_client not available
    class Counter:
        def __init__(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
    class Histogram:
        def __init__(self, *args, **kwargs):
            pass
        def observe(self, *args, **kwargs):
            pass
    class Gauge:
        def __init__(self, *args, **kwargs):
            pass
        def set(self, *args, **kwargs):
            pass
        def inc(self, *args, **kwargs):
            pass
        def dec(self, *args, **kwargs):
            pass
    def generate_latest():
        return b""

from src.logging.logger import get_logger

logger = get_logger(__name__)

# API Metrics
api_requests_total = Counter(
    "api_requests_total",
    "Total number of API requests",
    ["method", "endpoint", "status"]
)

api_request_duration = Histogram(
    "api_request_duration_seconds",
    "API request duration in seconds",
    ["method", "endpoint"]
)

# Database Metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Number of active database connections"
)

db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation"]
)

# GPT API Metrics
gpt_api_calls_total = Counter(
    "gpt_api_calls_total",
    "Total GPT API calls",
    ["model", "status"]
)

gpt_api_cost = Counter(
    "gpt_api_cost_usd",
    "Total GPT API cost in USD",
    ["model"]
)

# SEC Crawler Metrics
sec_downloads_total = Counter(
    "sec_downloads_total",
    "Total SEC filing downloads",
    ["status"]
)

sec_download_duration = Histogram(
    "sec_download_duration_seconds",
    "SEC download duration in seconds"
)

# Pipeline Metrics
pipeline_runs_total = Counter(
    "pipeline_runs_total",
    "Total pipeline runs",
    ["status"]
)

pipeline_duration = Histogram(
    "pipeline_duration_seconds",
    "Pipeline execution duration in seconds"
)


def get_metrics():
    """Get Prometheus metrics in text format."""
    if not PROMETHEUS_AVAILABLE:
        return "# Prometheus client not installed\n"
    return generate_latest().decode("utf-8")

