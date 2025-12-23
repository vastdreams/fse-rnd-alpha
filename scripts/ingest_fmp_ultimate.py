#!/usr/bin/env python
"""
PATH: scripts/ingest_fmp_ultimate.py
PURPOSE:
  - Ultimate tier FMP bulk ingestion for S&P 500 + full historical data.
  - Uses bulk endpoints for maximum efficiency.
  - 3,000 calls/min rate limit with 30+ years of data.

FMP DOCUMENTATION: https://site.financialmodelingprep.com/developer/docs
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import logging
import aiohttp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

import psycopg2
from psycopg2.extras import execute_values

# FMP API Configuration
FMP_BASE_URL = "https://financialmodelingprep.com"


class FMPUltimateClient:
    """Ultimate tier FMP client with bulk endpoint support."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.call_count = 0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _get(self, endpoint: str, params: Dict = None) -> Any:
        """Make GET request with rate limit tracking."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{FMP_BASE_URL}{endpoint}"
        params = params or {}
        params["apikey"] = self.api_key
        
        self.call_count += 1
        
        try:
            async with self.session.get(url, params=params, timeout=60) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 429:
                    logger.warning("Rate limited, waiting 1s...")
                    await asyncio.sleep(1)
                    return await self._get(endpoint, params)
                else:
                    logger.debug(f"API error {response.status}: {endpoint}")
                    return None
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    # === INDEX CONSTITUENTS ===
    async def get_sp500_constituents(self) -> List[Dict]:
        """Get S&P 500 constituents."""
        return await self._get("/stable/sp500-constituent") or []
    
    async def get_nasdaq_constituents(self) -> List[Dict]:
        """Get NASDAQ constituents."""
        return await self._get("/stable/nasdaq-constituent") or []
    
    async def get_dowjones_constituents(self) -> List[Dict]:
        """Get Dow Jones constituents."""
        return await self._get("/stable/dowjones-constituent") or []
    
    # === BULK FINANCIAL STATEMENTS ===
    async def get_income_statements_bulk(self, year: int, period: str = "annual") -> List[Dict]:
        """Bulk income statements for all companies in a year."""
        return await self._get("/stable/income-statement-bulk", {"year": year, "period": period}) or []
    
    async def get_balance_sheets_bulk(self, year: int, period: str = "annual") -> List[Dict]:
        """Bulk balance sheets for all companies in a year."""
        return await self._get("/stable/balance-sheet-statement-bulk", {"year": year, "period": period}) or []
    
    async def get_cash_flows_bulk(self, year: int, period: str = "annual") -> List[Dict]:
        """Bulk cash flows for all companies in a year."""
        return await self._get("/stable/cash-flow-statement-bulk", {"year": year, "period": period}) or []
    
    # === BULK METRICS ===
    async def get_key_metrics_ttm_bulk(self) -> List[Dict]:
        """Bulk TTM key metrics for all companies."""
        return await self._get("/stable/key-metrics-ttm-bulk") or []
    
    async def get_ratios_ttm_bulk(self) -> List[Dict]:
        """Bulk TTM ratios for all companies."""
        return await self._get("/stable/ratios-ttm-bulk") or []
    
    async def get_profiles_bulk(self, part: int = 0) -> List[Dict]:
        """Bulk company profiles."""
        return await self._get("/stable/profile-bulk", {"part": part}) or []
    
    # === BULK PRICES ===
    async def get_eod_bulk(self, date_str: str) -> List[Dict]:
        """Bulk end-of-day prices for all stocks on a date."""
        return await self._get("/stable/eod-bulk", {"date": date_str}) or []
    
    # === INDIVIDUAL HISTORICAL (for full history) ===
    async def get_historical_prices(self, symbol: str, from_date: str = None) -> List[Dict]:
        """Full historical prices for a symbol."""
        params = {"symbol": symbol}
        if from_date:
            params["from"] = from_date
        data = await self._get("/stable/historical-price-eod/full", params)
        return data if isinstance(data, list) else []


class FMPUltimateIngestor:
    """Bulk data ingestor using FMP Ultimate tier."""
    
    def __init__(self, api_key: str, db_url: str):
        self.api_key = api_key
        self.db_url = db_url
        self.conn = None
        self.start_year = 1995
        self.end_year = 2025
        
    def connect_db(self):
        """Connect to database."""
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
    
    def ensure_tables(self):
        """Create all required tables."""
        cursor = self.conn.cursor()
        
        # S&P 500 Companies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sp500_companies (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(255),
                sector VARCHAR(100),
                sub_sector VARCHAR(100),
                headquarters VARCHAR(200),
                cik VARCHAR(20),
                founded VARCHAR(20),
                added_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Company Profiles
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_profiles (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(255),
                sector VARCHAR(100),
                industry VARCHAR(150),
                exchange VARCHAR(50),
                market_cap NUMERIC,
                price NUMERIC,
                beta NUMERIC,
                vol_avg BIGINT,
                website VARCHAR(500),
                description TEXT,
                ceo VARCHAR(200),
                employees INT,
                ipo_date DATE,
                country VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Income Statements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_income_statements (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                period VARCHAR(10),
                date DATE,
                revenue NUMERIC,
                cost_of_revenue NUMERIC,
                gross_profit NUMERIC,
                rd_expenses NUMERIC,
                sga_expenses NUMERIC,
                operating_expenses NUMERIC,
                operating_income NUMERIC,
                interest_expense NUMERIC,
                ebitda NUMERIC,
                net_income NUMERIC,
                eps NUMERIC,
                eps_diluted NUMERIC,
                shares_out BIGINT,
                UNIQUE(symbol, fiscal_year, period)
            )
        """)
        
        # Balance Sheets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_balance_sheets (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                period VARCHAR(10),
                date DATE,
                total_assets NUMERIC,
                total_current_assets NUMERIC,
                cash_and_equivalents NUMERIC,
                total_liabilities NUMERIC,
                total_current_liabilities NUMERIC,
                long_term_debt NUMERIC,
                total_debt NUMERIC,
                total_equity NUMERIC,
                retained_earnings NUMERIC,
                UNIQUE(symbol, fiscal_year, period)
            )
        """)
        
        # Cash Flows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_cash_flows (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                period VARCHAR(10),
                date DATE,
                operating_cash_flow NUMERIC,
                investing_cash_flow NUMERIC,
                financing_cash_flow NUMERIC,
                capital_expenditure NUMERIC,
                free_cash_flow NUMERIC,
                dividends_paid NUMERIC,
                stock_repurchased NUMERIC,
                UNIQUE(symbol, fiscal_year, period)
            )
        """)
        
        # Daily Prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_daily_prices (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                date DATE,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                adj_close NUMERIC,
                volume BIGINT,
                change_pct NUMERIC,
                vwap NUMERIC,
                UNIQUE(symbol, date)
            )
        """)
        
        # Annual Returns (computed)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_annual_returns (
                symbol VARCHAR(20),
                year INT,
                annual_return NUMERIC,
                volatility NUMERIC,
                start_price NUMERIC,
                end_price NUMERIC,
                PRIMARY KEY(symbol, year)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_inc_sym ON fmp_income_statements(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_inc_yr ON fmp_income_statements(fiscal_year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_bal_sym ON fmp_balance_sheets(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_cf_sym ON fmp_cash_flows(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_pr_sym ON fmp_daily_prices(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_pr_dt ON fmp_daily_prices(date)")
        
        self.conn.commit()
        logger.info("Tables created")
    
    async def ingest_sp500_constituents(self) -> List[str]:
        """Fetch and store S&P 500 constituents."""
        async with FMPUltimateClient(self.api_key) as client:
            companies = await client.get_sp500_constituents()
        
        if not companies:
            logger.error("Failed to get S&P 500 constituents")
            return []
        
        cursor = self.conn.cursor()
        for c in companies:
            cursor.execute("""
                INSERT INTO sp500_companies (symbol, name, sector, sub_sector, headquarters, cik, founded)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name, sector = EXCLUDED.sector
            """, (
                c.get("symbol"), c.get("name"), c.get("sector"),
                c.get("subSector"), c.get("headQuarter"), c.get("cik"), c.get("founded")
            ))
        
        self.conn.commit()
        symbols = [c.get("symbol") for c in companies]
        logger.info(f"Stored {len(symbols)} S&P 500 constituents")
        return symbols
    
    async def ingest_profiles_bulk(self):
        """Ingest all company profiles in bulk."""
        cursor = self.conn.cursor()
        total = 0
        
        async with FMPUltimateClient(self.api_key) as client:
            # Profiles come in parts
            for part in range(10):  # Usually 0-9 parts
                profiles = await client.get_profiles_bulk(part)
                if not profiles:
                    break
                
                for p in profiles:
                    try:
                        cursor.execute("""
                            INSERT INTO fmp_profiles 
                            (symbol, name, sector, industry, exchange, market_cap, price, beta,
                             vol_avg, website, description, ceo, employees, ipo_date, country)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol) DO UPDATE SET
                                market_cap = EXCLUDED.market_cap, price = EXCLUDED.price
                        """, (
                            p.get("symbol"), p.get("companyName"), p.get("sector"),
                            p.get("industry"), p.get("exchange"), p.get("mktCap"),
                            p.get("price"), p.get("beta"), p.get("volAvg"),
                            p.get("website"), p.get("description"), p.get("ceo"),
                            p.get("fullTimeEmployees"), p.get("ipoDate"), p.get("country")
                        ))
                        total += 1
                    except:
                        continue
                
                self.conn.commit()
                logger.info(f"Profiles part {part}: {len(profiles)} records, total: {total}")
        
        return total
    
    async def ingest_financials_bulk(self):
        """Ingest all financial statements using bulk endpoints."""
        cursor = self.conn.cursor()
        years = list(range(self.start_year, self.end_year + 1))
        
        income_total = 0
        balance_total = 0
        cashflow_total = 0
        
        async with FMPUltimateClient(self.api_key) as client:
            for year in years:
                logger.info(f"Fetching year {year}...")
                
                # Fetch all three statement types for this year
                income, balance, cashflow = await asyncio.gather(
                    client.get_income_statements_bulk(year, "annual"),
                    client.get_balance_sheets_bulk(year, "annual"),
                    client.get_cash_flows_bulk(year, "annual")
                )
                
                # Store income statements
                for rec in (income or []):
                    try:
                        fy = rec.get("calendarYear") or (rec.get("date") or "0000")[:4]
                        cursor.execute("""
                            INSERT INTO fmp_income_statements
                            (symbol, fiscal_year, period, date, revenue, cost_of_revenue,
                             gross_profit, rd_expenses, sga_expenses, operating_expenses,
                             operating_income, interest_expense, ebitda, net_income, eps, eps_diluted, shares_out)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                revenue = EXCLUDED.revenue, rd_expenses = EXCLUDED.rd_expenses
                        """, (
                            rec.get("symbol"), int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("revenue"), rec.get("costOfRevenue"), rec.get("grossProfit"),
                            rec.get("researchAndDevelopmentExpenses"),
                            rec.get("sellingGeneralAndAdministrativeExpenses"),
                            rec.get("operatingExpenses"), rec.get("operatingIncome"),
                            rec.get("interestExpense"), rec.get("ebitda"), rec.get("netIncome"),
                            rec.get("eps"), rec.get("epsdiluted"), rec.get("weightedAverageShsOut")
                        ))
                        income_total += 1
                    except:
                        continue
                
                # Store balance sheets
                for rec in (balance or []):
                    try:
                        fy = rec.get("calendarYear") or (rec.get("date") or "0000")[:4]
                        cursor.execute("""
                            INSERT INTO fmp_balance_sheets
                            (symbol, fiscal_year, period, date, total_assets, total_current_assets,
                             cash_and_equivalents, total_liabilities, total_current_liabilities,
                             long_term_debt, total_debt, total_equity, retained_earnings)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                total_assets = EXCLUDED.total_assets
                        """, (
                            rec.get("symbol"), int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("totalAssets"), rec.get("totalCurrentAssets"),
                            rec.get("cashAndCashEquivalents"), rec.get("totalLiabilities"),
                            rec.get("totalCurrentLiabilities"), rec.get("longTermDebt"),
                            rec.get("totalDebt"), rec.get("totalStockholdersEquity"),
                            rec.get("retainedEarnings")
                        ))
                        balance_total += 1
                    except:
                        continue
                
                # Store cash flows
                for rec in (cashflow or []):
                    try:
                        fy = rec.get("calendarYear") or (rec.get("date") or "0000")[:4]
                        cursor.execute("""
                            INSERT INTO fmp_cash_flows
                            (symbol, fiscal_year, period, date, operating_cash_flow, investing_cash_flow,
                             financing_cash_flow, capital_expenditure, free_cash_flow, dividends_paid, stock_repurchased)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year, period) DO UPDATE SET
                                operating_cash_flow = EXCLUDED.operating_cash_flow
                        """, (
                            rec.get("symbol"), int(fy), rec.get("period", "FY"), rec.get("date"),
                            rec.get("operatingCashFlow"), rec.get("netCashUsedForInvestingActivites"),
                            rec.get("netCashUsedProvidedByFinancingActivities"),
                            rec.get("capitalExpenditure"), rec.get("freeCashFlow"),
                            rec.get("dividendsPaid"), rec.get("commonStockRepurchased")
                        ))
                        cashflow_total += 1
                    except:
                        continue
                
                self.conn.commit()
                logger.info(f"Year {year}: Inc={len(income or [])}, Bal={len(balance or [])}, CF={len(cashflow or [])}")
        
        logger.info(f"Total: Income={income_total}, Balance={balance_total}, CashFlow={cashflow_total}")
        return {"income": income_total, "balance": balance_total, "cashflow": cashflow_total}
    
    async def ingest_historical_prices(self, symbols: List[str]):
        """Ingest full historical prices for S&P 500 companies."""
        cursor = self.conn.cursor()
        total = 0
        
        async with FMPUltimateClient(self.api_key) as client:
            # Process in batches
            batch_size = 50
            
            for i in range(0, len(symbols), batch_size):
                batch = symbols[i:i + batch_size]
                
                # Fetch prices for batch in parallel
                tasks = [client.get_historical_prices(s, "1995-01-01") for s in batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for symbol, prices in zip(batch, results):
                    if isinstance(prices, Exception) or not prices:
                        continue
                    
                    for p in prices:
                        try:
                            cursor.execute("""
                                INSERT INTO fmp_daily_prices
                                (symbol, date, open, high, low, close, adj_close, volume, change_pct, vwap)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (symbol, date) DO NOTHING
                            """, (
                                symbol, p.get("date"), p.get("open"), p.get("high"),
                                p.get("low"), p.get("close"), p.get("adjClose"),
                                p.get("volume"), p.get("changePercent"), p.get("vwap")
                            ))
                            total += 1
                        except:
                            continue
                
                self.conn.commit()
                logger.info(f"Prices batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}: {total} total records")
        
        logger.info(f"Total price records: {total}")
        return total
    
    def compute_annual_returns(self):
        """Compute annual returns from daily prices."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO fmp_annual_returns (symbol, year, annual_return, volatility, start_price, end_price)
            SELECT 
                symbol,
                EXTRACT(YEAR FROM date)::INT as year,
                (MAX(CASE WHEN date = max_date THEN adj_close END) / 
                 NULLIF(MAX(CASE WHEN date = min_date THEN adj_close END), 0) - 1) as annual_return,
                STDDEV(daily_return) * SQRT(252) as volatility,
                MAX(CASE WHEN date = min_date THEN adj_close END) as start_price,
                MAX(CASE WHEN date = max_date THEN adj_close END) as end_price
            FROM (
                SELECT 
                    p.*,
                    (adj_close / NULLIF(LAG(adj_close) OVER (PARTITION BY symbol ORDER BY date), 0) - 1) as daily_return,
                    MIN(date) OVER (PARTITION BY symbol, EXTRACT(YEAR FROM date)) as min_date,
                    MAX(date) OVER (PARTITION BY symbol, EXTRACT(YEAR FROM date)) as max_date
                FROM fmp_daily_prices p
            ) sub
            GROUP BY symbol, EXTRACT(YEAR FROM date)
            ON CONFLICT (symbol, year) DO UPDATE SET
                annual_return = EXCLUDED.annual_return,
                volatility = EXCLUDED.volatility
        """)
        
        self.conn.commit()
        cursor.execute("SELECT COUNT(*) FROM fmp_annual_returns")
        count = cursor.fetchone()[0]
        logger.info(f"Computed {count} annual return records")
        return count
    
    async def run(self):
        """Run complete ingestion pipeline."""
        start = datetime.now()
        
        logger.info("=" * 70)
        logger.info("FMP ULTIMATE TIER BULK INGESTION")
        logger.info(f"Years: {self.start_year} - {self.end_year}")
        logger.info("=" * 70)
        
        self.connect_db()
        self.ensure_tables()
        
        # 1. Get S&P 500 constituents
        logger.info("\n[1/5] Fetching S&P 500 constituents...")
        symbols = await self.ingest_sp500_constituents()
        
        # 2. Bulk profiles
        logger.info("\n[2/5] Ingesting company profiles (bulk)...")
        profile_count = await self.ingest_profiles_bulk()
        
        # 3. Bulk financials (30 years x 3 statements = 90 API calls)
        logger.info("\n[3/5] Ingesting financial statements (bulk, 30 years)...")
        financial_counts = await self.ingest_financials_bulk()
        
        # 4. Historical prices for S&P 500
        logger.info("\n[4/5] Ingesting historical prices for S&P 500...")
        price_count = await self.ingest_historical_prices(symbols)
        
        # 5. Compute returns
        logger.info("\n[5/5] Computing annual returns...")
        return_count = self.compute_annual_returns()
        
        elapsed = (datetime.now() - start).total_seconds()
        
        logger.info("\n" + "=" * 70)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
        logger.info(f"S&P 500 Companies: {len(symbols)}")
        logger.info(f"Company Profiles: {profile_count}")
        logger.info(f"Income Statements: {financial_counts['income']}")
        logger.info(f"Balance Sheets: {financial_counts['balance']}")
        logger.info(f"Cash Flows: {financial_counts['cashflow']}")
        logger.info(f"Price Records: {price_count}")
        logger.info(f"Annual Returns: {return_count}")
        logger.info("=" * 70)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY"))
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = parser.parse_args()
    
    if not args.api_key or not args.db_url:
        print("ERROR: FMP_API_KEY and DATABASE_URL required")
        sys.exit(1)
    
    ingestor = FMPUltimateIngestor(args.api_key, args.db_url)
    asyncio.run(ingestor.run())


if __name__ == "__main__":
    main()

