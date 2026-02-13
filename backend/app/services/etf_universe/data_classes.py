"""
PATH: backend/app/services/etf_universe/data_classes.py
PURPOSE: Configuration constants and data classes for ETF universe eligibility
WHY: Separated from builder logic for clean I→O boundaries
FLOW:
  ┌──────────┐    ┌────────────────┐    ┌──────────────────┐
  │ Constants │ →  │ GateResult     │ →  │ EligibilityResult│
  └──────────┘    └────────────────┘    └──────────────────┘
DEPENDENCIES:
  - app.services.sanity_checks: MIN_REVENUE_THRESHOLD for financial validity
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from app.services.sanity_checks import MIN_REVENUE_THRESHOLD


# ==============================================================================
# Configuration Constants
# ==============================================================================

# Minimum listing age before formation date (prevents recent IPOs)
MIN_LISTING_AGE_DAYS = 365

# Minimum trailing trading days for liquidity assessment
MIN_LIQUIDITY_TRADING_DAYS = 60

# Minimum median daily dollar volume ($) for liquidity gate
MIN_LIQUIDITY_DOLLAR_VOLUME = 1_000_000  # $1M median daily volume

# Minimum revenue for financial validity
MIN_REVENUE = MIN_REVENUE_THRESHOLD  # $100M from sanity_checks


# ==============================================================================
# Data Classes
# ==============================================================================

class EligibilityMode(str, Enum):
    """Mode indicating how eligibility was determined."""
    PUBLISHED = "published"      # Full historical membership used
    PROVISIONAL = "provisional"  # Anti-lookahead gates used (membership unavailable)


@dataclass
class GateResult:
    """Result of applying a single eligibility gate."""
    gate_name: str
    passed_count: int
    failed_count: int
    failed_symbols: List[str] = field(default_factory=list)
    
    @property
    def pass_rate(self) -> float:
        total = self.passed_count + self.failed_count
        return self.passed_count / total if total > 0 else 0.0


@dataclass
class EligibilityResult:
    """Complete result of universe eligibility determination."""
    as_of_year: int
    formation_date: date
    mode: EligibilityMode
    
    # Eligible symbols
    eligible_symbols: List[str]
    
    # Gate results (for audit)
    gate_results: List[GateResult] = field(default_factory=list)
    
    # Coverage metrics
    total_candidates: int = 0
    membership_coverage: int = 0  # How many had historical membership data
    
    # Provenance
    warnings: List[str] = field(default_factory=list)
    
    @property
    def gates_applied(self) -> List[str]:
        return [g.gate_name for g in self.gate_results]
    
    def to_meta_dict(self) -> Dict:
        """Convert to dictionary for API response meta block."""
        return {
            "mode": self.mode.value,
            "formation_date": self.formation_date.isoformat(),
            "formation_date_rule": "July 1 of as_of_year (Fama-French convention)",
            "eligibility_gates_applied": self.gates_applied,
            "membership_coverage": self.membership_coverage,
            "total_candidates": self.total_candidates,
            "eligible_count": len(self.eligible_symbols),
            "exclusion_rate": 1.0 - (len(self.eligible_symbols) / self.total_candidates) if self.total_candidates > 0 else 0.0,
        }
