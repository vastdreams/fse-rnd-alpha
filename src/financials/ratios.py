"""Calculate financial ratios from canonical financial statements."""
from typing import Dict, Optional
from src.models.orm.financials_core import FinancialsCore


def calculate_ratios(financials: FinancialsCore) -> Dict[str, Optional[float]]:
    """
    Calculate all financial ratios from financials core.
    
    All division operations are protected against zero denominators.
    Returns None for ratios that cannot be calculated due to zero denominators.
    """
    ratios = {}
    
    # Helper function to safely divide
    def safe_divide(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        """Safely divide two numbers, returning None if division is invalid."""
        if numerator is None or denominator is None:
            return None
        if denominator == 0:
            return None
        try:
            return numerator / denominator
        except (TypeError, ValueError):
            return None
    
    # Profitability ratios (all require revenue > 0)
    if financials.revenue is not None and financials.revenue > 0:
        if financials.gross_profit is not None:
            ratios["gross_margin"] = safe_divide(financials.gross_profit, financials.revenue)
        if financials.operating_income is not None:
            ratios["operating_margin"] = safe_divide(financials.operating_income, financials.revenue)
        if financials.net_income is not None:
            ratios["net_margin"] = safe_divide(financials.net_income, financials.revenue)
        if financials.rd_expense is not None:
            ratios["rd_intensity"] = safe_divide(financials.rd_expense, financials.revenue)
    
    # Return ratios (require equity/assets > 0)
    if financials.total_equity is not None and financials.total_equity > 0:
        if financials.net_income is not None:
            ratios["roe"] = safe_divide(financials.net_income, financials.total_equity)
    
    if financials.total_assets is not None and financials.total_assets > 0:
        if financials.net_income is not None:
            ratios["roa"] = safe_divide(financials.net_income, financials.total_assets)
    
    # Leverage ratios
    if financials.total_equity is not None and financials.total_equity > 0:
        total_debt = (financials.short_term_debt or 0) + (financials.long_term_debt or 0)
        if total_debt > 0:
            ratios["debt_to_equity"] = safe_divide(total_debt, financials.total_equity)
    
    if financials.total_assets is not None and financials.total_assets > 0:
        total_debt = (financials.short_term_debt or 0) + (financials.long_term_debt or 0)
        if total_debt > 0:
            ratios["debt_to_assets"] = safe_divide(total_debt, financials.total_assets)
    
    # Interest coverage (requires interest_expense > 0)
    if financials.interest_expense is not None and financials.interest_expense > 0:
        if financials.ebit is not None:
            ratios["interest_coverage"] = safe_divide(financials.ebit, financials.interest_expense)
    
    # Cash flow ratios
    # CFO to Net Income: requires net_income != 0
    if financials.net_income is not None and financials.net_income != 0:
        if financials.cash_from_operations is not None:
            ratios["cfo_to_net_income"] = safe_divide(
                financials.cash_from_operations,
                financials.net_income
            )
    
    # Free Cash Flow
    if financials.cash_from_operations is not None and financials.capex is not None:
        ratios["fcf"] = financials.cash_from_operations - abs(financials.capex)
        # FCF Margin requires revenue > 0
        if financials.revenue is not None and financials.revenue > 0:
            if ratios["fcf"] is not None:
                ratios["fcf_margin"] = safe_divide(ratios["fcf"], financials.revenue)
    
    return ratios

