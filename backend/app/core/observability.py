"""Privacy-preserving error tracking for the API and Celery processes."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.config import settings


logger = logging.getLogger(__name__)
_initialized = False


def _strip_query_and_fragment(value: str) -> str:
    """Keep a route identity while removing arbitrary request values."""

    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return value.split("?", 1)[0].split("#", 1)[0]


def _scrub_request_context(event: dict[str, Any]) -> None:
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            for key in list(headers):
                if key.lower() in {"authorization", "cookie", "set-cookie", "x-api-key"}:
                    headers[key] = "[Filtered]"
        if "data" in request:
            request["data"] = "[Filtered]"
        if "query_string" in request:
            request["query_string"] = "[Filtered]"
        # Sentry's request URL can independently contain query/fragment data,
        # even when query_string has already been removed by an integration.
        url = request.get("url")
        if isinstance(url, str):
            request["url"] = _strip_query_and_fragment(url)
    # Integration and application extras can contain arbitrary exception input,
    # so they are not a safe observability export boundary.
    event.pop("extra", None)
    event.pop("user", None)


def scrub_error_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Retain operational context without exporting credentials or investor PII."""

    _scrub_request_context(event)
    return event


def scrub_transaction_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Apply the same privacy boundary to Sentry performance transactions."""

    _scrub_request_context(event)
    transaction = event.get("transaction")
    if isinstance(transaction, str):
        event["transaction"] = _strip_query_and_fragment(transaction)
    spans = event.get("spans")
    if isinstance(spans, list):
        for span in spans:
            if not isinstance(span, dict):
                continue
            # Span descriptions/data can contain SQL parameters, URL query
            # values, and task arguments. Keep only the bounded operation name.
            span.pop("description", None)
            span.pop("data", None)
    return event


def init_error_tracking() -> None:
    """Initialize Sentry only when the target provides an explicit DSN."""

    global _initialized
    if _initialized or not settings.SENTRY_DSN:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.SENTRY_ENVIRONMENT,
            integrations=[
                FastApiIntegration(),
                CeleryIntegration(),
                SqlalchemyIntegration(),
            ],
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
            before_send=scrub_error_event,
            before_send_transaction=scrub_transaction_event,
        )
        _initialized = True
        logger.info("Error tracking initialized for environment %s", settings.SENTRY_ENVIRONMENT)
    except Exception:  # Error tracking must never take down a release.
        logger.exception("Unable to initialize error tracking")
