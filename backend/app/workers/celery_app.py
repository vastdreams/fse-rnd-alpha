"""
PATH: backend/app/workers/celery_app.py
PURPOSE:
  - Celery application configuration
  - Task queue setup for concurrent processing

ROLE IN ARCHITECTURE:
  - Background task processing layer
"""

from celery import Celery

from app.core.config import settings
from app.core.observability import init_error_tracking


init_error_tracking()

celery_app = Celery(
    "rd_alpha_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Concurrency settings
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    
    # Rate limiting for SEC API
    task_annotations={
        "app.workers.tasks.crawl_company_task": {
            "rate_limit": "10/s",  # SEC rate limit
        },
    },
    
    # Task routing
    task_routes={
        "app.workers.tasks.crawl_company_task": {"queue": "crawl"},
        "app.workers.tasks.compute_factors_task": {"queue": "compute"},
    },
)
