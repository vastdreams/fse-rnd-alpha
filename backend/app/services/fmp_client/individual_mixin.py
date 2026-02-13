"""
PATH: backend/app/services/fmp_client/individual_mixin.py
PURPOSE: Per-symbol FMP API methods (statements, prices, profiles, dividends)
WHY: Groups single-company query methods separate from bulk ingestion
FLOW:
  ┌──────────┐    ┌──────────────────┐    ┌───────────────────────┐
  │ symbol   │ →  │ Per-symbol API   │ →  │ List[Dict] / Dict     │
  └──────────┘    └──────────────────┘    └───────────────────────┘
DEPENDENCIES:
  - base.py: _get() method (via mixin composition)
RELATED:
  - bulk_mixin.py: all-company bulk methods
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FMPIndividualMixin:
    """
    Mixin providing per-symbol data retrieval methods.
    
    Covers: S&P 500 constituents, individual financial statements,
    stock prices, company profiles, and dividends.
    
    Requires _get() method from FMPClientBase.
    """

    # =========================================================================
    # S&P 500 Constituents
    # =========================================================================

    async def get_sp500_constituents(self) -> List[Dict[str, Any]]:
        """
        Get current S&P 500 constituents.
        
        Returns:
            List of S&P 500 companies with symbol, name, sector, etc.
        """
        # Try stable endpoint first, fall back to v3
        data = await self._get("/stable/sp500-constituent")
        if not data:
            data = await self._get("/api/v3/sp500_constituent")
        return data or []

    async def get_historical_sp500_constituents(self) -> List[Dict[str, Any]]:
        """
        Get historical S&P 500 constituent changes.
        
        Returns:
            List of additions/removals from S&P 500.
        """
        # Try stable endpoint first, fall back to v3
        data = await self._get("/stable/historical/sp500-constituent")
        if not data:
            data = await self._get("/api/v3/historical/sp500_constituent")
        return data or []

    # =========================================================================
    # Individual Company Financial Statements
    # =========================================================================

    async def get_income_statements(
        self, 
        symbol: str, 
        limit: int = 40,
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get income statements for a specific company.
        
        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to retrieve.
            period: "annual" or "quarter".
            
        Returns:
            List of income statement records.
        """
        # Use stable endpoint
        data = await self._get(
            "/stable/income-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )
        return data or []

    async def get_balance_sheets(
        self, 
        symbol: str, 
        limit: int = 40,
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get balance sheets for a specific company.
        
        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to retrieve.
            period: "annual" or "quarter".
            
        Returns:
            List of balance sheet records.
        """
        # Use stable endpoint
        data = await self._get(
            "/stable/balance-sheet-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )
        return data or []

    async def get_cash_flows(
        self, 
        symbol: str, 
        limit: int = 40,
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get cash flow statements for a specific company.
        
        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to retrieve.
            period: "annual" or "quarter".
            
        Returns:
            List of cash flow statement records.
        """
        # Use stable endpoint
        data = await self._get(
            "/stable/cash-flow-statement",
            {"symbol": symbol, "period": period, "limit": limit}
        )
        return data or []

    async def get_key_metrics(
        self, 
        symbol: str, 
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Get key metrics for a specific company.
        
        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to retrieve.
            
        Returns:
            List of key metrics records.
        """
        data = await self._get(
            f"/api/v3/key-metrics/{symbol}",
            {"limit": limit}
        )
        return data or []

    async def get_financial_ratios(
        self, 
        symbol: str, 
        limit: int = 40
    ) -> List[Dict[str, Any]]:
        """
        Get financial ratios for a specific company.
        
        Args:
            symbol: Stock ticker symbol.
            limit: Number of periods to retrieve.
            
        Returns:
            List of ratio records.
        """
        data = await self._get(
            f"/api/v3/ratios/{symbol}",
            {"limit": limit}
        )
        return data or []

    # =========================================================================
    # Stock Prices
    # =========================================================================

    async def get_historical_prices(
        self, 
        symbol: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical daily prices for a company.
        
        Args:
            symbol: Stock ticker symbol.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
            
        Returns:
            List of daily price records.
        """
        # Use stable endpoint
        params = {"symbol": symbol}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        data = await self._get("/stable/historical-price-eod/full", params)
        
        if data and isinstance(data, list):
            return data
        if data and "historical" in data:
            return data["historical"]
        return []

    async def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile.
        
        Args:
            symbol: Stock ticker symbol.
            
        Returns:
            Company profile dictionary.
        """
        data = await self._get("/stable/profile", {"symbol": symbol})
        if data and isinstance(data, list) and len(data) > 0:
            return data[0]
        return None

    # =========================================================================
    # Corporate Actions (Dividends)
    # =========================================================================

    async def get_dividends(
        self,
        symbol: str,
    ) -> List[Dict[str, Any]]:
        """
        Get dividend events for a ticker.

        Notes:
          - Uses the FMP *stable* endpoint which is available on our current plan.
          - The returned `date` is the ex-dividend date (and can equal record date under T+1 settlement).
          - `adjDividend` is split-adjusted and is preferred when constructing total-return series
            from split-adjusted close prices.
        """
        data = await self._get("/stable/dividends", {"symbol": symbol})
        if isinstance(data, list):
            return data
        return []
