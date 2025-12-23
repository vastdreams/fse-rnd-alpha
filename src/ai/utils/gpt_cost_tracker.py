"""GPT API cost tracking and limits."""
from typing import Dict, Optional, List, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from src.logging.logger import get_logger

logger = get_logger(__name__)


# GPT model pricing (per 1K tokens) - Update as needed
MODEL_PRICING = {
    "gpt-4o": {"input": 0.005, "output": 0.015},  # $5/$15 per 1M tokens
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-5": {"input": 0.005, "output": 0.015},  # Estimated
    "gpt-5.1": {"input": 0.005, "output": 0.015},  # Estimated
}


@dataclass
class CostRecord:
    """Record of a single API call cost."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    prompt_hash: Optional[str] = None
    cached: bool = False


@dataclass
class CostLimits:
    """Cost limits configuration."""
    daily_limit: float = 100.0  # $100 per day
    monthly_limit: float = 1000.0  # $1000 per month
    per_request_limit: float = 10.0  # $10 per request
    warning_threshold: float = 0.8  # Warn at 80% of limit


class GPTCostTracker:
    """
    Track GPT API costs and enforce limits.
    
    Can be extended to use database for persistent storage.
    """
    
    def __init__(self, limits: Optional[CostLimits] = None):
        """
        Initialize cost tracker.
        
        Args:
            limits: Cost limits configuration
        """
        self.limits = limits or CostLimits()
        self.records: List[CostRecord] = []
        self.daily_cost: float = 0.0
        self.monthly_cost: float = 0.0
        self.last_reset_date: Optional[datetime] = None
    
    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost for API call.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in dollars
        """
        if model not in MODEL_PRICING:
            logger.warning(f"Unknown model pricing: {model}, using default")
            pricing = {"input": 0.005, "output": 0.015}
        else:
            pricing = MODEL_PRICING[model]
        
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def record_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        prompt_hash: Optional[str] = None,
        cached: bool = False
    ) -> CostRecord:
        """
        Record an API call and its cost.
        
        Args:
            model: Model name
            input_tokens: Input tokens
            output_tokens: Output tokens
            prompt_hash: Hash of prompt (for tracking)
            cached: Whether response was from cache
            
        Returns:
            CostRecord instance
        """
        # Reset daily/monthly counters if needed
        self._reset_if_needed()
        
        # Calculate cost
        cost = 0.0 if cached else self.calculate_cost(model, input_tokens, output_tokens)
        
        # Create record
        record = CostRecord(
            timestamp=datetime.now(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            prompt_hash=prompt_hash,
            cached=cached,
        )
        
        # Add to records
        self.records.append(record)
        
        # Update totals
        if not cached:
            self.daily_cost += cost
            self.monthly_cost += cost
        
        # Check limits
        self._check_limits(record)
        
        logger.debug(f"Recorded API call: {model}, {input_tokens}+{output_tokens} tokens, ${cost:.4f}")
        
        return record
    
    def _reset_if_needed(self):
        """Reset daily/monthly counters if new day/month."""
        now = datetime.now()
        
        if self.last_reset_date is None:
            self.last_reset_date = now
            return
        
        # Reset daily if new day
        if now.date() > self.last_reset_date.date():
            self.daily_cost = 0.0
            logger.info("Daily cost counter reset")
        
        # Reset monthly if new month
        if now.month != self.last_reset_date.month or now.year != self.last_reset_date.year:
            self.monthly_cost = 0.0
            logger.info("Monthly cost counter reset")
        
        self.last_reset_date = now
    
    def _check_limits(self, record: CostRecord):
        """Check cost limits and warn if exceeded."""
        if record.cached:
            return
        
        # Check per-request limit
        if record.cost > self.limits.per_request_limit:
            logger.error(
                f"API call cost (${record.cost:.2f}) exceeds per-request limit "
                f"(${self.limits.per_request_limit:.2f})"
            )
        
        # Check daily limit
        daily_threshold = self.limits.daily_limit * self.limits.warning_threshold
        if self.daily_cost >= self.limits.daily_limit:
            logger.error(
                f"Daily cost limit exceeded: ${self.daily_cost:.2f} / ${self.limits.daily_limit:.2f}"
            )
        elif self.daily_cost >= daily_threshold:
            logger.warning(
                f"Approaching daily cost limit: ${self.daily_cost:.2f} / ${self.limits.daily_limit:.2f}"
            )
        
        # Check monthly limit
        monthly_threshold = self.limits.monthly_limit * self.limits.warning_threshold
        if self.monthly_cost >= self.limits.monthly_limit:
            logger.error(
                f"Monthly cost limit exceeded: ${self.monthly_cost:.2f} / ${self.limits.monthly_limit:.2f}"
            )
        elif self.monthly_cost >= monthly_threshold:
            logger.warning(
                f"Approaching monthly cost limit: ${self.monthly_cost:.2f} / ${self.limits.monthly_limit:.2f}"
            )
    
    def get_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get cost statistics.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with statistics
        """
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_records = [
            r for r in self.records
            if r.timestamp >= cutoff_date
        ]
        
        total_cost = sum(r.cost for r in recent_records)
        total_calls = len(recent_records)
        cached_calls = sum(1 for r in recent_records if r.cached)
        
        # Cost by model
        cost_by_model: Dict[str, float] = {}
        for record in recent_records:
            cost_by_model[record.model] = cost_by_model.get(record.model, 0.0) + record.cost
        
        return {
            "period_days": days,
            "total_cost": total_cost,
            "total_calls": total_calls,
            "cached_calls": cached_calls,
            "cache_hit_rate": cached_calls / total_calls if total_calls > 0 else 0.0,
            "average_cost_per_call": total_cost / total_calls if total_calls > 0 else 0.0,
            "daily_cost": self.daily_cost,
            "monthly_cost": self.monthly_cost,
            "cost_by_model": cost_by_model,
            "limits": {
                "daily": self.limits.daily_limit,
                "monthly": self.limits.monthly_limit,
                "per_request": self.limits.per_request_limit,
            },
        }
    
    def can_make_request(self, estimated_cost: float) -> Tuple[bool, Optional[str]]:
        """
        Check if request can be made within limits.
        
        Args:
            estimated_cost: Estimated cost of request
            
        Returns:
            Tuple of (can_make, reason_if_not)
        """
        self._reset_if_needed()
        
        # Check per-request limit
        if estimated_cost > self.limits.per_request_limit:
            return False, f"Estimated cost (${estimated_cost:.2f}) exceeds per-request limit"
        
        # Check daily limit
        if self.daily_cost + estimated_cost > self.limits.daily_limit:
            return False, f"Would exceed daily limit (${self.daily_cost + estimated_cost:.2f} > ${self.limits.daily_limit:.2f})"
        
        # Check monthly limit
        if self.monthly_cost + estimated_cost > self.limits.monthly_limit:
            return False, f"Would exceed monthly limit (${self.monthly_cost + estimated_cost:.2f} > ${self.limits.monthly_limit:.2f})"
        
        return True, None


# Global tracker instance
_cost_tracker: Optional[GPTCostTracker] = None


def get_cost_tracker(limits: Optional[CostLimits] = None) -> GPTCostTracker:
    """
    Get cost tracker instance (singleton).
    
    Args:
        limits: Cost limits (only used on first call)
        
    Returns:
        GPTCostTracker instance
    """
    global _cost_tracker
    
    if _cost_tracker is None:
        _cost_tracker = GPTCostTracker(limits=limits)
    
    return _cost_tracker

