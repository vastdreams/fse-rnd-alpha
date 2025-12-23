"""Progress tracking utilities for long-running operations."""
from typing import Optional, Callable, Dict, Any
from datetime import datetime
from src.logging.logger import get_logger

logger = get_logger(__name__)


class ProgressTracker:
    """
    Track progress of long-running operations.
    
    Can be used with or without tqdm (gracefully degrades if tqdm not available).
    """
    
    def __init__(
        self,
        total: int,
        description: str = "Processing",
        unit: str = "item",
        use_tqdm: bool = True,
    ):
        """
        Initialize progress tracker.
        
        Args:
            total: Total number of items to process
            description: Description of the operation
            unit: Unit name (item, company, filing, etc.)
            use_tqdm: Whether to use tqdm if available
        """
        self.total = total
        self.description = description
        self.unit = unit
        self.current = 0
        self.start_time = datetime.now()
        self.use_tqdm = use_tqdm
        self._tqdm_bar = None
        
        # Initialize tqdm if available and requested
        if use_tqdm:
            try:
                from tqdm import tqdm
                self._tqdm_bar = tqdm(
                    total=total,
                    desc=description,
                    unit=unit,
                    bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]'
                )
            except ImportError:
                logger.debug("tqdm not available, using simple progress tracking")
                self.use_tqdm = False
        
        logger.info(f"Starting {description}: {total} {unit}(s)")
    
    def update(self, n: int = 1, status: Optional[str] = None):
        """
        Update progress.
        
        Args:
            n: Number of items completed
            status: Optional status message
        """
        self.current += n
        
        if self._tqdm_bar:
            self._tqdm_bar.update(n)
            if status:
                self._tqdm_bar.set_postfix_str(status)
        else:
            # Simple logging-based progress
            percentage = (self.current / self.total) * 100 if self.total > 0 else 0
            elapsed = (datetime.now() - self.start_time).total_seconds()
            
            if self.current % max(1, self.total // 10) == 0 or self.current == self.total:
                # Log every 10% or at completion
                logger.info(
                    f"{self.description}: {self.current}/{self.total} ({percentage:.1f}%) - "
                    f"Elapsed: {elapsed:.1f}s" + (f" - {status}" if status else "")
                )
    
    def set_description(self, description: str):
        """Update description."""
        self.description = description
        if self._tqdm_bar:
            self._tqdm_bar.set_description(description)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current progress statistics."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        
        # Calculate rate and ETA
        if elapsed > 0 and self.current > 0:
            rate = self.current / elapsed
            remaining = self.total - self.current
            eta_seconds = remaining / rate if rate > 0 else None
        else:
            rate = 0.0
            eta_seconds = None
        
        return {
            "current": self.current,
            "total": self.total,
            "percentage": percentage,
            "elapsed_seconds": elapsed,
            "rate_per_second": rate,
            "eta_seconds": eta_seconds,
            "description": self.description,
        }
    
    def close(self):
        """Close progress tracker."""
        if self._tqdm_bar:
            self._tqdm_bar.close()
        
        elapsed = (datetime.now() - self.start_time).total_seconds()
        logger.info(f"Completed {self.description}: {self.current}/{self.total} in {elapsed:.1f}s")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def track_progress(total: int, description: str = "Processing", unit: str = "item"):
    """
    Context manager for progress tracking.
    
    Usage:
        with track_progress(100, "Crawling companies", "company") as tracker:
            for item in items:
                # Process item
                tracker.update(1)
    """
    return ProgressTracker(total, description, unit)

