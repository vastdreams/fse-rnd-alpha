#!/usr/bin/env python
"""
PATH: scripts/ingest_fmp_financials.py
PURPOSE:
  - Ingest financial statements for S&P 500 using individual company endpoints.
  - FMP bulk financial endpoints return CSV; this uses JSON endpoints.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging
import aiohttp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import psycopg2

FMP_BASE_URL = "https://financialmodelingprep.com"


class FMPFinancialsIngestor:
    """Ingest financial statements using per-company endpoints."""
    
    def __init__(self, api_key: str, db_url: str, max_concurrent: int = 20):
        self.api_key = api_key
        self.db_url = db_url
        self.max_concurrent = max_concurrent
        self.conn = None
        self.session = None
        
    def connect_db(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.db_url)
        self.conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/')
        )
        logger.info("Database connected")
    
    async def _get(self, endpoint: str, params: Dict = None) -> Any:
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{FMP_BASE_URL}{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key
        
        for attempt in range(3):
            try:
                async with self.session.get(url, params=params, timeout=30) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 429:
                        await asyncio.sleep(1 + attempt)
                        continue
                    return None
            except:
                await asyncio.sleep(0.5)
        return None
    
    async def get_income_statements(self, symbol: str) -> List[Dict]:
        return await self._get("/stable/income-statement", {"symbol": symbol, "period": "annual", "limit": 35}) or []
    
    async def get_balance_sheets(self, symbol: str) -> List[Dict]:
        return await self._get("/stable/balance-sheet-statement", {"symbol": symbol, "period": "annual", "limit": 35}) or []
    
    async def get_cash_flows(self, symbol: str) -> List[Dict]:
        return await self._get("/stable/cash-flow-statement", {"symbol": symbol, "period": "annual", "limit": 35}) or []
    
    async def get_key_metrics(self, symbol: str) -> List[Dict]:
        return await self._get("/stable/key-metrics", {"symbol": symbol, "period": "annual", "limit": 35}) or []
    
    async def get_ratios(self, symbol: str) -> List[Dict]:
        return await self._get("/stable/ratios", {"symbol": symbol, "period": "annual", "limit": 35}) or []
    
    async def fetch_company_financials(self, symbol: str) -> Dict:
        """Fetch all financials for a company."""
        income, balance, cashflow, metrics, ratios = await asyncio.gather(
            self.get_income_statements(symbol),
            self.get_balance_sheets(symbol),
            self.get_cash_flows(symbol),
            self.get_key_metrics(symbol),
            self.get_ratios(symbol),
            return_exceptions=True
        )
        
        return {
            "symbol": symbol,
            "income": income if isinstance(income, list) else [],
            "balance": balance if isinstance(balance, list) else [],
            "cashflow": cashflow if isinstance(cashflow, list) else [],
            "metrics": metrics if isinstance(metrics, list) else [],
            "ratios": ratios if isinstance(ratios, list) else [],
        }
    
    def get_sp500_symbols(self) -> List[str]:
        """Get S&P 500 symbols from database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT symbol FROM sp500_companies ORDER BY symbol")
        return [r[0] for r in cursor.fetchall()]
    
    async def ingest_all(self, symbols: List[str]):
        """Ingest financials for all symbols."""
        cursor = self.conn.cursor()
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        income_count = 0
        balance_count = 0
        cashflow_count = 0
        
        async def process_symbol(symbol: str):
            async with semaphore:
                return await self.fetch_company_financials(symbol)
        
        # Process in batches
        batch_size = 50
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            tasks = [process_symbol(s) for s in batch]
            results = await asyncio.gather(*tasks)
            
            for data in results:
                symbol = data["symbol"]
                
                # Store income statements
                for rec in data["income"]:
                    try:
                        fy = rec.get("calendarYear") or str(rec.get("date", "0000"))[:4]
                        cursor.execute("""
                            INSERT INTO fmp_income_statements
                            (symbol, fiscal_year, period, date, revenue, cost_of_revenue,
                             gross_profit, rd_expenses, sga_expenses, operating_expenses,
                             operating_income, interest_expense, ebitda, net_income, eps, eps_diluted, shares_out)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                revenue = EXCLUDED.revenue, rd_expenses = EXCLUDED.rd_expenses,
                                net_income = EXCLUDED.net_income
                        """, (
                            symbol, int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("revenue"), rec.get("costOfRevenue"), rec.get("grossProfit"),
                            rec.get("researchAndDevelopmentExpenses"),
                            rec.get("sellingGeneralAndAdministrativeExpenses"),
                            rec.get("operatingExpenses"), rec.get("operatingIncome"),
                            rec.get("interestExpense"), rec.get("ebitda"), rec.get("netIncome"),
                            rec.get("eps"), rec.get("epsdiluted"), rec.get("weightedAverageShsOut")
                        ))
                        income_count += 1
                    except Exception as e:
                        pass
                
                # Store balance sheets
                for rec in data["balance"]:
                    try:
                        fy = rec.get("calendarYear") or str(rec.get("date", "0000"))[:4]
                        cursor.execute("""
                            INSERT INTO fmp_balance_sheets
                            (symbol, fiscal_year, period, date, total_assets, total_current_assets,
                             cash_and_equivalents, total_liabilities, total_current_liabilities,
                             long_term_debt, total_debt, total_equity, retained_earnings)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                total_assets = EXCLUDED.total_assets, total_equity = EXCLUDED.total_equity
                        """, (
                            symbol, int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("totalAssets"), rec.get("totalCurrentAssets"),
                            rec.get("cashAndCashEquivalents"), rec.get("totalLiabilities"),
                            rec.get("totalCurrentLiabilities"), rec.get("longTermDebt"),
                            rec.get("totalDebt"), rec.get("totalStockholdersEquity"),
                            rec.get("retainedEarnings")
                        ))
                        balance_count += 1
                    except:
                        pass
                
                # Store cash flows
                for rec in data["cashflow"]:
                    try:
                        fy = rec.get("calendarYear") or str(rec.get("date", "0000"))[:4]
                        cursor.execute("""
                            INSERT INTO fmp_cash_flows
                            (symbol, fiscal_year, period, date, operating_cash_flow, investing_cash_flow,
                             financing_cash_flow, capital_expenditure, free_cash_flow, dividends_paid, stock_repurchased)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                operating_cash_flow = EXCLUDED.operating_cash_flow,
                                free_cash_flow = EXCLUDED.free_cash_flow
                        """, (
                            symbol, int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("operatingCashFlow"), rec.get("netCashUsedForInvestingActivites"),
                            rec.get("netCashUsedProvidedByFinancingActivities"),
                            rec.get("capitalExpenditure"), rec.get("freeCashFlow"),
                            rec.get("dividendsPaid"), rec.get("commonStockRepurchased")
                        ))
                        cashflow_count += 1
                    except:
                        pass
            
            self.conn.commit()
            logger.info(f"Batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}: "
                       f"Inc={income_count}, Bal={balance_count}, CF={cashflow_count}")
        
        return {"income": income_count, "balance": balance_count, "cashflow": cashflow_count}
    
    async def run(self):
        start = datetime.now()
        logger.info("=" * 60)
        logger.info("FMP FINANCIAL STATEMENTS INGESTION")
        logger.info("=" * 60)
        
        self.connect_db()
        self.session = aiohttp.ClientSession()
        
        symbols = self.get_sp500_symbols()
        logger.info(f"Found {len(symbols)} S&P 500 symbols")
        
        counts = await self.ingest_all(symbols)
        
        await self.session.close()
        
        elapsed = (datetime.now() - start).total_seconds()
        logger.info("=" * 60)
        logger.info("COMPLETE")
        logger.info(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info(f"Income Statements: {counts['income']}")
        logger.info(f"Balance Sheets: {counts['balance']}")
        logger.info(f"Cash Flows: {counts['cashflow']}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY"))
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--concurrent", type=int, default=20)
    args = parser.parse_args()
    
    if not args.api_key or not args.db_url:
        print("ERROR: FMP_API_KEY and DATABASE_URL required")
        sys.exit(1)
    
    ingestor = FMPFinancialsIngestor(args.api_key, args.db_url, args.concurrent)
    asyncio.run(ingestor.run())


if __name__ == "__main__":
    main()

