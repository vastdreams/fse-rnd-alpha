"""Database transaction safety enhancements."""
from contextlib import contextmanager
from typing import Generator, Optional, Callable
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from src.db.connection import db_session_scope
from src.logging.logger import get_logger

logger = get_logger(__name__)


class TransactionError(Exception):
    """Base exception for transaction errors."""
    pass


class TransactionRetryError(TransactionError):
    """Raised when transaction retries are exhausted."""
    pass


@contextmanager
def safe_transaction(
    max_retries: int = 3,
    retry_on: Optional[tuple] = None,
    isolation_level: Optional[str] = None
) -> Generator[Session, None, None]:
    """
    Enhanced database transaction with retry logic and error handling.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_on: Tuple of exception types to retry on (default: OperationalError)
        isolation_level: Optional isolation level (READ COMMITTED, REPEATABLE READ, SERIALIZABLE)
        
    Yields:
        Database session
        
    Raises:
        TransactionRetryError: If all retries are exhausted
        SQLAlchemyError: For non-retryable errors
    """
    if retry_on is None:
        retry_on = (OperationalError,)
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with db_session_scope() as session:
                # Set isolation level if specified
                if isolation_level:
                    try:
                        session.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                    except Exception as e:
                        logger.warning(f"Could not set isolation level: {e}")
                
                yield session
                # Success - exit retry loop
                return
                
        except retry_on as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"Transaction error (attempt {attempt + 1}/{max_retries}): {e}. Retrying..."
                )
                import time
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Transaction failed after {max_retries} attempts: {e}")
                raise TransactionRetryError(f"Transaction failed after {max_retries} attempts") from e
                
        except IntegrityError as e:
            # Integrity errors (constraints, etc.) are not retryable
            logger.error(f"Integrity error in transaction: {e}")
            raise
            
        except SQLAlchemyError as e:
            # Other SQLAlchemy errors - log and re-raise
            logger.error(f"SQLAlchemy error in transaction: {e}")
            raise
            
        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error in transaction: {e}", exc_info=True)
            raise


@contextmanager
def read_only_transaction() -> Generator[Session, None, None]:
    """
    Read-only transaction for queries that don't modify data.
    
    Provides better performance and prevents accidental writes.
    """
    with db_session_scope() as session:
        try:
            # Set transaction to read-only (PostgreSQL)
            session.execute("SET TRANSACTION READ ONLY")
            yield session
        except Exception as e:
            logger.debug(f"Could not set read-only mode (may not be supported): {e}")
            yield session


def transactional(
    max_retries: int = 3,
    retry_on: Optional[tuple] = None
):
    """
    Decorator for functions that need database transactions.
    
    Usage:
        @transactional(max_retries=3)
        def update_company(company_id: int, data: dict):
            session = get_session()  # Get session from context
            # ... do work
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            with safe_transaction(max_retries=max_retries, retry_on=retry_on) as session:
                # Inject session if function accepts it
                import inspect
                sig = inspect.signature(func)
                if 'session' in sig.parameters:
                    kwargs['session'] = session
                
                return func(*args, **kwargs)
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def bulk_operation_safe(
    operations: list[Callable],
    batch_size: int = 100,
    continue_on_error: bool = False
) -> dict:
    """
    Safely execute bulk database operations with batching and error handling.
    
    Args:
        operations: List of callable operations to execute
        batch_size: Number of operations per batch
        continue_on_error: Whether to continue on errors
        
    Returns:
        Dictionary with operation results
    """
    results = {
        "total": len(operations),
        "succeeded": 0,
        "failed": 0,
        "errors": [],
    }
    
    # Process in batches
    for batch_start in range(0, len(operations), batch_size):
        batch = operations[batch_start:batch_start + batch_size]
        
        try:
            with safe_transaction() as session:
                for operation in batch:
                    try:
                        operation(session)
                        results["succeeded"] += 1
                    except Exception as e:
                        results["failed"] += 1
                        error_info = {
                            "operation": str(operation),
                            "error": str(e),
                        }
                        results["errors"].append(error_info)
                        
                        if not continue_on_error:
                            raise
                        
                        logger.warning(f"Operation failed but continuing: {e}")
        except Exception as e:
            if not continue_on_error:
                raise
            logger.error(f"Batch failed but continuing: {e}")
    
    logger.info(
        f"Bulk operation completed: {results['succeeded']}/{results['total']} succeeded"
    )
    
    return results


def check_transaction_health() -> dict:
    """
    Check transaction system health.
    
    Returns:
        Health status dictionary
    """
    try:
        with safe_transaction() as session:
            # Test basic query
            from sqlalchemy import text
            result = session.execute(text("SELECT 1"))
            result.fetchone()
            
            return {
                "status": "healthy",
                "transaction_support": True,
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }

