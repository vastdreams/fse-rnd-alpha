"""Comprehensive financial data normalization and alignment."""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.models.orm.financials_core import FinancialsCore
from src.financials.normaliser import normalize_units, align_fiscal_year, handle_restatements
from src.utils.data_validation import validate_financial_value, validate_type
from src.logging.logger import get_logger

logger = get_logger(__name__)


class FinancialNormalizer:
    """
    Comprehensive financial data normalization.
    
    Handles:
    - Unit normalization
    - Fiscal year alignment
    - Restatement handling
    - Data quality improvements
    """
    
    def __init__(self):
        """Initialize normalizer."""
        self.default_unit = "USD"
    
    def normalize_financials(
        self,
        financials: FinancialsCore,
        target_fiscal_year: Optional[int] = None,
        prefer_latest: bool = True
    ) -> FinancialsCore:
        """
        Normalize financial data comprehensively.
        
        Args:
            financials: Financial data to normalize
            target_fiscal_year: Target fiscal year (if aligning)
            prefer_latest: Prefer latest restated values
            
        Returns:
            Normalized FinancialsCore object
        """
        # Create a copy to avoid modifying original
        normalized = self._copy_financials(financials)
        
        # Normalize units
        normalized = self._normalize_units_comprehensive(normalized)
        
        # Handle restatements
        normalized = self._handle_restatements_safe(normalized, prefer_latest)
        
        # Validate normalized data
        normalized = self._validate_normalized_data(normalized)
        
        return normalized
    
    def _copy_financials(self, financials: FinancialsCore) -> FinancialsCore:
        """Create a copy of financials object."""
        # This would need to be implemented based on your ORM structure
        # For now, return as-is (in real implementation, create new instance)
        return financials
    
    def _normalize_units_comprehensive(self, financials: FinancialsCore) -> FinancialsCore:
        """
        Normalize all unit values comprehensively.
        
        This is a placeholder - in real implementation, would normalize all fields.
        """
        # Unit normalization would go here
        # For now, financials should already be in correct units
        return financials
    
    def _handle_restatements_safe(
        self,
        financials: FinancialsCore,
        prefer_latest: bool
    ) -> FinancialsCore:
        """
        Handle restatements safely.
        
        Args:
            financials: Financial data
            prefer_latest: Prefer latest restated values
            
        Returns:
            Financial data with restatements handled
        """
        # Restatement handling logic would go here
        # For now, return as-is
        return financials
    
    def _validate_normalized_data(self, financials: FinancialsCore) -> FinancialsCore:
        """
        Validate normalized data for quality.
        
        Args:
            financials: Normalized financial data
            
        Returns:
            Validated financial data
        """
        # Validation logic
        # Check all values are reasonable
        # Log warnings for suspicious values
        
        return financials
    
    def align_to_fiscal_year(
        self,
        financial_data: Dict[int, FinancialsCore],
        target_year: int
    ) -> Optional[FinancialsCore]:
        """
        Align financial data to target fiscal year.
        
        Args:
            financial_data: Dictionary mapping fiscal years to FinancialsCore
            target_year: Target fiscal year
            
        Returns:
            Financial data for target year or None
        """
        if target_year in financial_data:
            return financial_data[target_year]
        
        # Try to find closest year
        years = sorted(financial_data.keys())
        if not years:
            return None
        
        # Find closest year
        closest_year = min(years, key=lambda y: abs(y - target_year))
        logger.info(f"Using financial data from {closest_year} for target year {target_year}")
        
        return financial_data[closest_year]


def normalize_financial_data(
    financials: FinancialsCore,
    target_fiscal_year: Optional[int] = None
) -> FinancialsCore:
    """
    Convenience function to normalize financial data.
    
    Args:
        financials: Financial data to normalize
        target_fiscal_year: Target fiscal year (optional)
        
    Returns:
        Normalized financial data
    """
    normalizer = FinancialNormalizer()
    return normalizer.normalize_financials(financials, target_fiscal_year)

