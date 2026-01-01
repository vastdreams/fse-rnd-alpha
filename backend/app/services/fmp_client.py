# PATH: backend/app/services/fmp_client.py
# PURPOSE:
#   - Financial Modeling Prep (FMP) API client for bulk data ingestion.
#   - Fetches financial statements, ratios, and stock prices.
#
# ROLE IN ARCHITECTURE:
#   - Data ingestion service layer.
#
# MAIN EXPORTS:
#   - FMPClient: Async client for FMP API.
#
# NON-RESPONSIBILITIES:
#   - Does not handle database persistence (see ingestion scripts).
#
# NOTES FOR FUTURE AI:
#   - FMP bulk endpoints return all companies at once for a given year.
#   - Use asyncio for parallel fetching across years.

import os
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# FMP API Configuration
FMP_BASE_URL = "https://financialmodelingprep.com"
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")


class FMPClient:
    """
    Async client for Financial Modeling Prep API.
    
    Provides methods for bulk data retrieval optimized for
    large-scale ingestion (500+ companies, 30+ years).
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FMP client.
        
        Args:
            api_key: FMP API key. Falls back to FMP_API_KEY env var.
        """
        self.api_key = api_key or FMP_API_KEY
        if not self.api_key:
            raise ValueError("FMP API key required. Set FMP_API_KEY env var.")
        
        self.base_url = FMP_BASE_URL
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _get(self, endpoint: str, params: Optional[Dict] = None, retries: int = 3) -> Any:
        """
        Make GET request to FMP API with retry logic.
        
        Args:
            endpoint: API endpoint path.
            params: Query parameters.
            retries: Number of retries for rate limits.
            
        Returns:
            JSON response data.
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key
        
        for attempt in range(retries):
            try:
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 429:
                        # Rate limited - wait and retry
                        wait_time = (2 ** attempt) * 2  # 2, 4, 8 seconds
                        logger.warning(f"Rate limited, waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    elif response.status == 402:
                        # Payment required - don't retry
                        logger.debug(f"402 Payment required for {endpoint}")
                        return None
                    else:
                        logger.error(f"FMP API error: {response.status} for {endpoint}")
                        return None
            except Exception as e:
                logger.error(f"FMP request failed: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None
        
        return None
    
    # =========================================================================
    # S&P 500 Constituents
    # =========================================================================
    
    async def get_sp500_constituents(self) -> List[Dict[str, Any]]:
        """
        Get current S&P 500 constituents.
        
        Returns:
            List of S&P 500 companies with symbol, name, sector, etc.
        """
        data = await self._get("/api/v3/sp500_constituent")
        return data or []
    
    async def get_historical_sp500_constituents(self) -> List[Dict[str, Any]]:
        """
        Get historical S&P 500 constituent changes.
        
        Returns:
            List of additions/removals from S&P 500.
        """
        data = await self._get("/api/v3/historical/sp500_constituent")
        return data or []
    
    # =========================================================================
    # Bulk Financial Statements
    # =========================================================================
    
    async def get_income_statements_bulk(
        self, 
        year: int, 
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get income statements for all companies in bulk.
        
        Args:
            year: Fiscal year.
            period: "annual" or quarter (Q1, Q2, Q3, Q4).
            
        Returns:
            List of income statement records.
        """
        data = await self._get(
            "/stable/income-statement-bulk",
            {"year": year, "period": period}
        )
        return data or []
    
    async def get_balance_sheets_bulk(
        self, 
        year: int, 
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get balance sheets for all companies in bulk.
        
        Args:
            year: Fiscal year.
            period: "annual" or quarter.
            
        Returns:
            List of balance sheet records.
        """
        data = await self._get(
            "/stable/balance-sheet-statement-bulk",
            {"year": year, "period": period}
        )
        return data or []
    
    async def get_cash_flows_bulk(
        self, 
        year: int, 
        period: str = "annual"
    ) -> List[Dict[str, Any]]:
        """
        Get cash flow statements for all companies in bulk.
        
        Args:
            year: Fiscal year.
            period: "annual" or quarter.
            
        Returns:
            List of cash flow statement records.
        """
        data = await self._get(
            "/stable/cash-flow-statement-bulk",
            {"year": year, "period": period}
        )
        return data or []
    
    async def get_key_metrics_ttm_bulk(self) -> List[Dict[str, Any]]:
        """
        Get trailing twelve months key metrics for all companies.
        
        Returns:
            List of key metrics records.
        """
        data = await self._get("/stable/key-metrics-ttm-bulk")
        return data or []
    
    async def get_ratios_ttm_bulk(self) -> List[Dict[str, Any]]:
        """
        Get trailing twelve months financial ratios for all companies.
        
        Returns:
            List of ratio records.
        """
        data = await self._get("/stable/ratios-ttm-bulk")
        return data or []
    
    async def get_profile_bulk(self, part: int = 0) -> List[Dict[str, Any]]:
        """
        Get company profiles in bulk.
        
        Args:
            part: Pagination part (0, 1, 2, ...).
            
        Returns:
            List of company profile records.
        """
        data = await self._get("/stable/profile-bulk", {"part": part})
        return data or []
    
    # =========================================================================
    # Individual Company Data (for targeted queries)
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
    
    async def get_eod_bulk(self, date_str: str) -> List[Dict[str, Any]]:
        """
        Get end-of-day prices for all stocks on a specific date.
        
        Args:
            date_str: Date in YYYY-MM-DD format.
            
        Returns:
            List of EOD price records.
        """
        data = await self._get("/stable/eod-bulk", {"date": date_str})
        return data or []
    
    # =========================================================================
    # Batch Fetching Utilities
    # =========================================================================
    
    async def fetch_all_years_financials(
        self,
        start_year: int = 1995,
        end_year: int = 2025,
        max_concurrent: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all financial statements for all years in parallel.
        
        Args:
            start_year: First year to fetch.
            end_year: Last year to fetch.
            max_concurrent: Maximum concurrent requests.
            
        Returns:
            Dictionary with income_statements, balance_sheets, cash_flows keys.
        """
        years = list(range(start_year, end_year + 1))
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_year(year: int, statement_type: str):
            async with semaphore:
                if statement_type == "income":
                    return await self.get_income_statements_bulk(year)
                elif statement_type == "balance":
                    return await self.get_balance_sheets_bulk(year)
                elif statement_type == "cashflow":
                    return await self.get_cash_flows_bulk(year)
        
        # Fetch all statement types for all years
        tasks = []
        task_info = []
        
        for year in years:
            for stmt_type in ["income", "balance", "cashflow"]:
                tasks.append(fetch_year(year, stmt_type))
                task_info.append((year, stmt_type))
        
        logger.info(f"Fetching {len(tasks)} financial statement batches...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize results
        all_data = {
            "income_statements": [],
            "balance_sheets": [],
            "cash_flows": []
        }
        
        for (year, stmt_type), result in zip(task_info, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching {stmt_type} for {year}: {result}")
                continue
            
            if result:
                if stmt_type == "income":
                    all_data["income_statements"].extend(result)
                elif stmt_type == "balance":
                    all_data["balance_sheets"].extend(result)
                elif stmt_type == "cashflow":
                    all_data["cash_flows"].extend(result)
        
        logger.info(
            f"Fetched: {len(all_data['income_statements'])} income, "
            f"{len(all_data['balance_sheets'])} balance, "
            f"{len(all_data['cash_flows'])} cashflow records"
        )
        
        return all_data
    
    async def fetch_prices_for_symbols(
        self,
        symbols: List[str],
        from_date: str = "1995-01-01",
        max_concurrent: int = 20
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical prices for multiple symbols in parallel.
        
        Args:
            symbols: List of stock ticker symbols.
            from_date: Start date for price history.
            max_concurrent: Maximum concurrent requests.
            
        Returns:
            Dictionary mapping symbol to list of price records.
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_symbol_prices(symbol: str):
            async with semaphore:
                return symbol, await self.get_historical_prices(symbol, from_date)
        
        logger.info(f"Fetching prices for {len(symbols)} symbols...")
        
        tasks = [fetch_symbol_prices(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        prices = {}
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Price fetch error: {result}")
                continue
            symbol, data = result
            prices[symbol] = data
        
        total_records = sum(len(p) for p in prices.values())
        logger.info(f"Fetched {total_records} total price records for {len(prices)} symbols")
        
        return prices


# ============================================================================
# Convenience Functions
# ============================================================================

async def test_fmp_connection(api_key: str) -> bool:
    """
    Test FMP API connection.
    
    Args:
        api_key: FMP API key.
        
    Returns:
        True if connection successful.
    """
    async with FMPClient(api_key) as client:
        sp500 = await client.get_sp500_constituents()
        if sp500:
            logger.info(f"FMP connection OK. Found {len(sp500)} S&P 500 companies.")
            return True
        return False

