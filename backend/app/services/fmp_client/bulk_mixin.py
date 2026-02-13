"""
PATH: backend/app/services/fmp_client/bulk_mixin.py
PURPOSE: Bulk financial statement methods and batch fetching utilities
WHY: Groups high-throughput bulk ingestion methods (all-company, all-year)
FLOW:
  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐
  │ year / symbols  │ →  │ Bulk FMP calls   │ →  │ List[Dict] records   │
  └─────────────────┘    └──────────────────┘    └──────────────────────┘
DEPENDENCIES:
  - asyncio: parallel fetching
  - base.py: _get() method (via mixin composition)
RELATED:
  - individual_mixin.py: per-symbol methods
"""

import asyncio
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FMPBulkMixin:
    """
    Mixin providing bulk financial statement retrieval and batch utilities.
    
    Requires _get() method from FMPClientBase.
    """

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
