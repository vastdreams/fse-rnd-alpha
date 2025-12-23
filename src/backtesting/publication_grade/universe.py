# PATH: src/backtesting/publication_grade/universe.py
# PURPOSE:
#   - Handle universe definition for backtests
#   - Track historical constituent membership
#   - Address survivorship bias
#
# ROLE IN ARCHITECTURE:
#   - Universe management for publication-grade analysis
#
# METHODOLOGY:
#   - "Current constituents" = S&P 500 as of today
#   - "Historical constituents" = all firms that were ever in S&P 500
#   - Point-in-time membership requires tracking additions/removals
#
# NOTES FOR FUTURE AI:
#   - Survivorship bias is a KNOWN issue with current implementation
#   - Paper claims must match actual universe used
#   - For publication: either implement historical or soften claims

import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class UniverseType(Enum):
    """Type of universe for backtest."""
    CURRENT_CONSTITUENTS = "current"      # Today's S&P 500 members
    HISTORICAL_CONSTITUENTS = "historical"  # All firms ever in S&P 500
    PILOT_COMPANIES = "pilot"              # Manually selected test set


@dataclass
class UniverseMembership:
    """
    Membership record for a company in an index.
    
    For proper point-in-time analysis, we need:
    - When the company was added
    - When (if) the company was removed
    - Reason for removal (delisting, M&A, etc.)
    """
    ticker: str
    cik: Optional[str] = None
    name: Optional[str] = None
    
    # Membership period
    added_date: Optional[date] = None
    removed_date: Optional[date] = None
    removal_reason: Optional[str] = None  # "delisted", "acquired", "dropped"
    
    # Current status
    is_current_member: bool = True
    
    def is_member_at(self, query_date: date) -> bool:
        """Check if company was member at a specific date."""
        if self.added_date and query_date < self.added_date:
            return False
        if self.removed_date and query_date >= self.removed_date:
            return False
        return True


@dataclass
class UniverseDefinition:
    """
    Complete universe definition for a backtest.
    
    This should be stored and versioned so results are reproducible.
    """
    name: str
    universe_type: UniverseType
    description: str
    
    # Member list
    members: List[UniverseMembership] = field(default_factory=list)
    
    # Metadata
    as_of_date: date = field(default_factory=date.today)
    data_source: str = ""
    
    # Survivorship bias flags
    includes_delisted: bool = False
    is_point_in_time: bool = False
    
    def get_members_at(self, query_date: date) -> List[str]:
        """Get list of tickers that were members at a specific date."""
        return [
            m.ticker for m in self.members 
            if m.is_member_at(query_date)
        ]
    
    def get_current_members(self) -> List[str]:
        """Get current members only."""
        return [m.ticker for m in self.members if m.is_current_member]


class UniverseManager:
    """
    Manage universe definitions for backtests.
    
    KEY METHODOLOGICAL ISSUE:
    If you claim "all S&P 500 constituents 1994-2024" but only use
    CURRENT constituents, you have survivorship bias. Companies that
    were removed (failed, acquired) are excluded, biasing results upward.
    
    Options:
    1. Use current constituents but CLEARLY STATE this in paper
    2. Implement historical constituent tracking
    3. Use a different claim ("firms with available data")
    """
    
    def __init__(self, session=None):
        self.session = session
        self._universes = {}
    
    def get_pilot_universe(self) -> UniverseDefinition:
        """
        Get pilot test universe (10 manually selected companies).
        This is fine for testing but not for publication.
        """
        from src.ingestion.universe_builder import get_pilot_companies
        
        pilot = get_pilot_companies()
        
        members = [
            UniverseMembership(
                ticker=c["ticker"],
                cik=c.get("cik"),
                name=c.get("name"),
                is_current_member=True
            )
            for c in pilot
        ]
        
        return UniverseDefinition(
            name="pilot_top10",
            universe_type=UniverseType.PILOT_COMPANIES,
            description="10 manually selected large-cap companies for testing",
            members=members,
            data_source="config/universe.yml",
            includes_delisted=False,
            is_point_in_time=False
        )
    
    def get_current_sp500_universe(self) -> UniverseDefinition:
        """
        Get current S&P 500 constituents.
        
        WARNING: This has survivorship bias for historical analysis.
        """
        from src.models.orm.company import Company
        
        members = []
        
        if self.session:
            companies = self.session.query(Company).all()
            members = [
                UniverseMembership(
                    ticker=c.ticker,
                    cik=c.cik,
                    name=c.name,
                    is_current_member=True
                )
                for c in companies
            ]
        
        return UniverseDefinition(
            name="sp500_current",
            universe_type=UniverseType.CURRENT_CONSTITUENTS,
            description=(
                "Current S&P 500 constituents. "
                "WARNING: Using for historical analysis introduces survivorship bias."
            ),
            members=members,
            data_source="database",
            includes_delisted=False,
            is_point_in_time=False
        )
    
    def validate_universe_claim(
        self,
        paper_claim: str,
        actual_universe: UniverseDefinition
    ) -> Dict:
        """
        Validate that paper claims match actual universe.
        
        Returns warnings if there's a mismatch.
        """
        warnings = []
        
        # Check survivorship
        if "1994" in paper_claim or "historical" in paper_claim.lower():
            if not actual_universe.is_point_in_time:
                warnings.append(
                    "SURVIVORSHIP BIAS: Paper claims historical period but "
                    "universe is not point-in-time. Companies that were removed "
                    "during the study period are excluded."
                )
        
        if "all constituents" in paper_claim.lower():
            if not actual_universe.includes_delisted:
                warnings.append(
                    "MISSING DELISTINGS: Paper claims 'all constituents' but "
                    "delisted companies are not included."
                )
        
        return {
            "claim": paper_claim,
            "actual_type": actual_universe.universe_type.value,
            "n_members": len(actual_universe.members),
            "is_valid": len(warnings) == 0,
            "warnings": warnings
        }
    
    def get_recommended_paper_claim(
        self,
        universe: UniverseDefinition
    ) -> str:
        """
        Generate a paper claim that accurately describes the universe.
        """
        if universe.universe_type == UniverseType.CURRENT_CONSTITUENTS:
            return (
                f"We study {len(universe.members)} companies that are current constituents "
                f"of the S&P 500 as of {universe.as_of_date}. We analyze historical data "
                f"for these firms, acknowledging that this approach may introduce survivorship bias "
                f"as companies that were removed from the index during our study period are excluded."
            )
        
        elif universe.universe_type == UniverseType.HISTORICAL_CONSTITUENTS:
            return (
                f"We study all {len(universe.members)} companies that have been constituents "
                f"of the S&P 500 at any point during our study period, including firms that "
                f"were subsequently removed due to delisting, acquisition, or index rebalancing."
            )
        
        elif universe.universe_type == UniverseType.PILOT_COMPANIES:
            return (
                f"We study {len(universe.members)} large-capitalization companies "
                f"selected for their data availability and representation across sectors."
            )
        
        return f"Universe of {len(universe.members)} companies."

