"""
PATH: backend/app/core/logging.py
PURPOSE: Structured logging with JSON output, specialized methods for formulas/API/computation chains
EXPORTS: StructuredLogger, get_logger, set_request_id, get_request_id, log_execution_time, log_async_execution_time
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from app.core.config import settings

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            log_data["request_id"] = request_id
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        _skip = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "message", "asctime",
        }
        for key, value in record.__dict__.items():
            if key not in _skip:
                try:
                    json.dumps(value)
                    log_data[key] = value
                except TypeError:
                    log_data[key] = str(value)
        return json.dumps(log_data, default=str)


class StructuredLogger:
    """Enhanced logger with specialized methods for R&D research application."""

    def __init__(self, name: str, use_json: Optional[bool] = None):
        self.logger = logging.getLogger(name)
        self.name = name
        if not self.logger.handlers:
            self._setup_handlers(use_json)

    def _setup_handlers(self, use_json: Optional[bool]) -> None:
        if use_json is None:
            use_json = not settings.DEBUG
        handler = logging.StreamHandler(sys.stdout)
        if use_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.logger.error(message, extra=kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        self.logger.exception(message, extra=kwargs)

    def log_formula(
        self,
        formula_name: str,
        inputs: Dict[str, Any],
        output: Any,
        duration_ms: float = 0.0,
        valid: bool = True,
        error: Optional[str] = None,
    ) -> None:
        self.logger.info(
            f"Formula: {formula_name}",
            extra={
                "event_type": "formula_execution",
                "component": self.name,
                "formula": formula_name,
                "inputs": inputs,
                "output": output,
                "output_valid": valid,
                "validation_error": error,
                "duration_ms": round(duration_ms, 3),
            },
        )

    def log_api(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        request_size: int = 0,
        response_size: int = 0,
        error: Optional[str] = None,
    ) -> None:
        level = logging.INFO if status_code < 400 else logging.ERROR
        self.logger.log(
            level,
            f"{method} {endpoint} -> {status_code}",
            extra={
                "event_type": "api_request",
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 3),
                "request_size_bytes": request_size,
                "response_size_bytes": response_size,
                "error": error,
            },
        )

    def log_step(
        self,
        step_name: str,
        step_number: int,
        total_steps: int,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
    ) -> None:
        self.logger.info(
            f"Step {step_number}/{total_steps}: {step_name}",
            extra={
                "event_type": "computation_step",
                "component": self.name,
                "step_name": step_name,
                "step_number": step_number,
                "total_steps": total_steps,
                "step_data": data or {},
                "duration_ms": round(duration_ms, 3),
            },
        )

    def log_db_query(
        self,
        operation: str,
        table: str,
        rows_affected: int = 0,
        duration_ms: float = 0.0,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.logger.debug(
            f"DB {operation} on {table}: {rows_affected} rows",
            extra={
                "event_type": "db_query",
                "operation": operation,
                "table": table,
                "rows_affected": rows_affected,
                "duration_ms": round(duration_ms, 3),
                "query_params": query_params or {},
            },
        )

    def log_cache(
        self,
        operation: str,
        key: str,
        hit: bool,
        duration_ms: float = 0.0,
    ) -> None:
        self.logger.debug(
            f"Cache {operation}: {'HIT' if hit else 'MISS'}",
            extra={
                "event_type": "cache_operation",
                "operation": operation,
                "cache_key": key,
                "cache_hit": hit,
                "duration_ms": round(duration_ms, 3),
            },
        )


def get_logger(name: str, use_json: Optional[bool] = None) -> StructuredLogger:
    return StructuredLogger(name, use_json)


def set_request_id(request_id: Optional[str] = None) -> str:
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    return request_id_var.get()


F = TypeVar("F", bound=Callable[..., Any])


def log_execution_time(logger: StructuredLogger) -> Callable[[F], F]:
    """Decorator to log function execution time."""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    f"Function {func.__name__} completed",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 3),
                    success=True,
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    f"Function {func.__name__} failed: {e}",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 3),
                    success=False,
                    error=str(e),
                )
                raise
        return wrapper  # type: ignore
    return decorator


def log_async_execution_time(logger: StructuredLogger) -> Callable[[F], F]:
    """Decorator to log async function execution time."""
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                logger.debug(
                    f"Async function {func.__name__} completed",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 3),
                    success=True,
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    f"Async function {func.__name__} failed: {e}",
                    function=func.__name__,
                    duration_ms=round(duration_ms, 3),
                    success=False,
                    error=str(e),
                )
                raise
        return wrapper  # type: ignore
    return decorator
