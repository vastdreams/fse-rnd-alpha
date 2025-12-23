#!/usr/bin/env python
"""
PATH: scripts/ingest_fmp_sp500.py
PURPOSE:
  - Fetch S&P 500 companies data from FMP API using stable endpoints.
  - Works with standard FMP subscription tier.
  - Fetches data company by company with concurrency.

ROLE IN ARCHITECTURE:
  - Primary data ingestion script for FMP data.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
import json

# Setup path
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

sys.path.insert(0, str(ROOT / "backend"))
from app.services.fmp_client import FMPClient

# S&P 500 tickers (current constituents - updated Dec 2024)
SP500_TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "JPM", "V",
    "UNH", "XOM", "MA", "JNJ", "PG", "HD", "CVX", "ABBV", "MRK", "COST",
    "LLY", "KO", "PEP", "WMT", "AVGO", "BAC", "TMO", "ORCL", "MCD", "CSCO",
    "ACN", "CRM", "ABT", "DHR", "ADBE", "AMD", "NKE", "TXN", "NFLX", "WFC",
    "PM", "LIN", "NEE", "UNP", "QCOM", "RTX", "LOW", "INTC", "INTU", "HON",
    "AMGN", "IBM", "SPGI", "CAT", "COP", "GE", "ISRG", "BA", "AMAT", "GS",
    "ELV", "PLD", "NOW", "BKNG", "BLK", "DE", "MDLZ", "SBUX", "VRTX", "T",
    "ADP", "MMC", "TJX", "LMT", "ADI", "GILD", "REGN", "CVS", "SYK", "PGR",
    "BMY", "SCHW", "C", "CB", "LRCX", "AMT", "MO", "ETN", "FI", "ZTS",
    "CI", "SO", "PANW", "BDX", "DUK", "SLB", "PNC", "CME", "EOG", "BSX",
    "MU", "USB", "ICE", "NOC", "ITW", "EQIX", "WM", "TGT", "CSX", "AON",
    "CL", "MCO", "PYPL", "GD", "APD", "SHW", "FCX", "MMM", "EMR", "ORLY",
    "PH", "KLAC", "NSC", "HUM", "MCK", "SNPS", "MAR", "CDNS", "TDG", "ROP",
    "CTAS", "ECL", "MSI", "CMG", "AJG", "PSX", "PCAR", "HCA", "FDX", "APH",
    "PSA", "NXPI", "AFL", "MCHP", "AZO", "ADSK", "CARR", "OXY", "TFC", "MPC",
    "AEP", "MET", "NEM", "AIG", "MSCI", "SRE", "GM", "TRV", "F", "EW",
    "TEL", "GWW", "CCI", "DXCM", "VLO", "WELL", "FTNT", "KMB", "JCI", "HLT",
    "MNST", "O", "PCG", "SPG", "STZ", "D", "ALL", "OKE", "BK", "ROST",
    "KDP", "AMP", "BIIB", "PAYX", "GIS", "A", "CTSH", "LHX", "PRU", "IDXX",
    "HSY", "DHI", "CPRT", "ON", "ED", "YUM", "HES", "BKR", "NUE", "FAST",
    "EXC", "CMI", "IQV", "VRSK", "PEG", "CTVA", "XEL", "DOW", "KR", "GEHC",
    "CDW", "DD", "RMD", "EA", "CBRE", "VMC", "PPG", "ODFL", "ROK", "KHC",
    "GLW", "KEYS", "CNC", "WEC", "ANSS", "MLM", "ACGL", "IT", "AWK", "MPWR",
    "GPN", "DLTR", "EFX", "DLR", "EXR", "FANG", "WST", "AVB", "EIX", "HAL",
    "TRGP", "RCL", "DAL", "PWR", "GRMN", "WTW", "EBAY", "HPQ", "VICI", "FTV",
    "XYL", "MTD", "TSCO", "SBAC", "CHD", "TTWO", "ALGN", "BRO", "ZBH", "LYV",
    "SYY", "CAH", "FITB", "WBD", "AEE", "EQR", "VTR", "TROW", "WAB", "FE",
    "UAL", "STT", "LEN", "NDAQ", "BALL", "DG", "ULTA", "DOV", "HBAN", "MTB",
    "K", "TDY", "RF", "CSGP", "CNP", "MOH", "ES", "PHM", "PTC", "PPL",
    "IRM", "CAG", "ETR", "HUBB", "COO", "WRB", "MAA", "NTAP", "DTE", "INVH",
    "MKC", "EL", "FDS", "CLX", "STE", "EXPD", "TER", "AKAM", "WAT", "LUV",
    "ARE", "J", "NTRS", "IFF", "CINF", "CFG", "IP", "TSN", "DRI", "GPC",
    "LDOS", "BBY", "JBHT", "WDC", "HOLX", "LYB", "DFS", "WRK", "SNA", "POOL",
    "ESS", "TYL", "ATO", "PKG", "CE", "FFIV", "LNT", "BG", "L", "CF",
    "KEY", "SWK", "SWKS", "EVRG", "PNR", "KIM", "NI", "CRL", "GEN", "AVY",
    "MOS", "INCY", "IPG", "HST", "TECH", "JKHY", "LKQ", "NDSN", "ALLE", "WY",
    "MKTX", "MGM", "EMN", "REG", "TPR", "PFG", "VTRS", "BWA", "AOS", "SJM",
    "CPB", "TXT", "AES", "CHRW", "TAP", "RHI", "UDR", "AAL", "CMA", "QRVO",
    "AIZ", "LW", "NRG", "HSIC", "UHS", "WYNN", "PNW", "HII", "BXP", "FRT",
    "HRL", "AMCR", "CPT", "IEX", "CBOE", "PAYC", "ROL", "WBA", "DVA", "GL",
    "MTCH", "BEN", "FOXA", "FOX", "CZR", "SOLV", "FMC", "GNRC", "RLJ", "BIO",
    "PARA", "MHK", "BBWI", "NWSA", "NWS", "CE", "ETSY", "COR", "EPAM", "CTLT",
]


class FMPSP500Ingestor:
    """Ingest S&P 500 data using FMP stable endpoints."""
    
    def __init__(self, api_key: str, db_url: str, max_concurrent: int = 10):
        self.api_key = api_key
        self.db_url = db_url
        self.max_concurrent = max_concurrent
        self.conn = None
        
    def connect_db(self):
        """Establish database connection."""
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
        """Create required database tables."""
        cursor = self.conn.cursor()
        
        # FMP Companies
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_companies (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(255),
                sector VARCHAR(100),
                industry VARCHAR(100),
                cik VARCHAR(20),
                exchange VARCHAR(50),
                market_cap NUMERIC,
                ipo_date DATE,
                ceo VARCHAR(200),
                website VARCHAR(500),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # FMP Financials (combined income/balance/cashflow)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_financials (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                date DATE,
                -- Income Statement
                revenue NUMERIC,
                cost_of_revenue NUMERIC,
                gross_profit NUMERIC,
                rd_expenses NUMERIC,
                sga_expenses NUMERIC,
                operating_income NUMERIC,
                net_income NUMERIC,
                ebitda NUMERIC,
                eps NUMERIC,
                eps_diluted NUMERIC,
                -- Balance Sheet
                total_assets NUMERIC,
                total_liabilities NUMERIC,
                total_equity NUMERIC,
                cash_and_equivalents NUMERIC,
                total_debt NUMERIC,
                -- Cash Flow
                operating_cash_flow NUMERIC,
                free_cash_flow NUMERIC,
                capital_expenditure NUMERIC,
                dividends_paid NUMERIC,
                -- Ratios
                rd_intensity NUMERIC,
                gross_margin NUMERIC,
                operating_margin NUMERIC,
                net_margin NUMERIC,
                roe NUMERIC,
                roa NUMERIC,
                debt_to_equity NUMERIC,
                current_ratio NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fiscal_year)
            )
        """)
        
        # Stock Prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_prices (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                date DATE,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                adj_close NUMERIC,
                volume BIGINT,
                UNIQUE(symbol, date)
            )
        """)
        
        # Annual Returns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_returns (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                year INT,
                annual_return NUMERIC,
                volatility NUMERIC,
                sharpe_ratio NUMERIC,
                max_drawdown NUMERIC,
                UNIQUE(symbol, year)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_fin_symbol ON fmp_financials(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_fin_year ON fmp_financials(fiscal_year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_prices_symbol ON fmp_prices(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_prices_date ON fmp_prices(date)")
        
        self.conn.commit()
        logger.info("Tables created")
    
    async def fetch_company_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch all data for a single company with rate limiting."""
        async with FMPClient(self.api_key) as client:
            # Fetch sequentially with delays to avoid rate limits
            await asyncio.sleep(0.5)  # Rate limit delay
            
            profile = await client.get_company_profile(symbol)
            await asyncio.sleep(0.3)
            
            # Prices work on free tier
            prices = await client.get_historical_prices(symbol, from_date="1995-01-01")
            await asyncio.sleep(0.3)
            
            # These may fail on free tier (402) - that's OK
            income = await client.get_income_statements(symbol, limit=35)
            balance = await client.get_balance_sheets(symbol, limit=35)
            cashflow = await client.get_cash_flows(symbol, limit=35)
            
            return {
                "symbol": symbol,
                "profile": profile if not isinstance(profile, Exception) else None,
                "income": income if income and not isinstance(income, Exception) else [],
                "balance": balance if balance and not isinstance(balance, Exception) else [],
                "cashflow": cashflow if cashflow and not isinstance(cashflow, Exception) else [],
                "prices": prices if prices and not isinstance(prices, Exception) else [],
            }
    
    async def ingest_all_companies(self, symbols: List[str]):
        """Ingest data for all symbols with concurrency control."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        cursor = self.conn.cursor()
        
        async def process_symbol(symbol: str, idx: int):
            async with semaphore:
                try:
                    data = await self.fetch_company_data(symbol)
                    await asyncio.sleep(0.1)  # Small delay for rate limiting
                    return data
                except Exception as e:
                    logger.error(f"{symbol}: Error - {e}")
                    return None
        
        # Process all symbols
        total = len(symbols)
        logger.info(f"Starting ingestion for {total} symbols...")
        
        tasks = [process_symbol(s, i) for i, s in enumerate(symbols)]
        
        # Process in batches for better memory management
        batch_size = 50
        companies_stored = 0
        financials_stored = 0
        prices_stored = 0
        
        for batch_start in range(0, len(tasks), batch_size):
            batch_tasks = tasks[batch_start:batch_start + batch_size]
            results = await asyncio.gather(*batch_tasks)
            
            for data in results:
                if not data:
                    continue
                
                symbol = data["symbol"]
                
                # Store profile
                if data["profile"]:
                    p = data["profile"]
                    try:
                        cursor.execute("""
                            INSERT INTO fmp_companies 
                            (symbol, name, sector, industry, cik, exchange, market_cap, 
                             ipo_date, ceo, website, description)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol) DO UPDATE SET
                                name = EXCLUDED.name,
                                sector = EXCLUDED.sector,
                                market_cap = EXCLUDED.market_cap,
                                updated_at = CURRENT_TIMESTAMP
                        """, (
                            symbol, p.get("companyName"), p.get("sector"),
                            p.get("industry"), p.get("cik"), p.get("exchange"),
                            p.get("marketCap"), p.get("ipoDate"), p.get("ceo"),
                            p.get("website"), p.get("description")
                        ))
                        companies_stored += 1
                    except Exception as e:
                        logger.debug(f"{symbol} profile error: {e}")
                
                # Merge and store financials
                income_by_year = {int(r.get("fiscalYear") or r.get("date", "0")[:4]): r 
                                  for r in (data["income"] or []) if r.get("fiscalYear") or r.get("date")}
                balance_by_year = {int(r.get("fiscalYear") or r.get("date", "0")[:4]): r 
                                   for r in (data["balance"] or []) if r.get("fiscalYear") or r.get("date")}
                cashflow_by_year = {int(r.get("fiscalYear") or r.get("date", "0")[:4]): r 
                                    for r in (data["cashflow"] or []) if r.get("fiscalYear") or r.get("date")}
                
                all_years = set(income_by_year.keys()) | set(balance_by_year.keys())
                
                for year in all_years:
                    if year < 1990 or year > 2030:
                        continue
                    
                    inc = income_by_year.get(year, {})
                    bal = balance_by_year.get(year, {})
                    cf = cashflow_by_year.get(year, {})
                    
                    revenue = inc.get("revenue")
                    rd = inc.get("researchAndDevelopmentExpenses")
                    net_income = inc.get("netIncome")
                    total_equity = bal.get("totalStockholdersEquity")
                    total_assets = bal.get("totalAssets")
                    
                    # Compute ratios
                    rd_intensity = (rd / revenue) if revenue and rd else None
                    gross_margin = (inc.get("grossProfit") / revenue) if revenue and inc.get("grossProfit") else None
                    operating_margin = (inc.get("operatingIncome") / revenue) if revenue and inc.get("operatingIncome") else None
                    net_margin = (net_income / revenue) if revenue and net_income else None
                    roe = (net_income / total_equity) if total_equity and net_income else None
                    roa = (net_income / total_assets) if total_assets and net_income else None
                    
                    try:
                        cursor.execute("""
                            INSERT INTO fmp_financials
                            (symbol, fiscal_year, date, revenue, cost_of_revenue, gross_profit,
                             rd_expenses, sga_expenses, operating_income, net_income, ebitda,
                             eps, eps_diluted, total_assets, total_liabilities, total_equity,
                             cash_and_equivalents, total_debt, operating_cash_flow, free_cash_flow,
                             capital_expenditure, dividends_paid, rd_intensity, gross_margin,
                             operating_margin, net_margin, roe, roa, debt_to_equity, current_ratio)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, fiscal_year) DO UPDATE SET
                                revenue = EXCLUDED.revenue,
                                rd_expenses = EXCLUDED.rd_expenses,
                                net_income = EXCLUDED.net_income,
                                rd_intensity = EXCLUDED.rd_intensity
                        """, (
                            symbol, year, inc.get("date"),
                            revenue, inc.get("costOfRevenue"), inc.get("grossProfit"),
                            rd, inc.get("sellingGeneralAndAdministrativeExpenses"),
                            inc.get("operatingIncome"), net_income, inc.get("ebitda"),
                            inc.get("eps"), inc.get("epsDiluted"),
                            total_assets, bal.get("totalLiabilities"), total_equity,
                            bal.get("cashAndCashEquivalents"), bal.get("totalDebt"),
                            cf.get("operatingCashFlow"), cf.get("freeCashFlow"),
                            cf.get("capitalExpenditure"), cf.get("dividendsPaid"),
                            rd_intensity, gross_margin, operating_margin, net_margin,
                            roe, roa, None, None
                        ))
                        financials_stored += 1
                    except Exception as e:
                        logger.debug(f"{symbol} {year} financial error: {e}")
                
                # Store prices
                for p in (data["prices"] or [])[:7000]:  # Limit per symbol
                    try:
                        cursor.execute("""
                            INSERT INTO fmp_prices (symbol, date, open, high, low, close, adj_close, volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, date) DO NOTHING
                        """, (
                            symbol, p.get("date"), p.get("open"), p.get("high"),
                            p.get("low"), p.get("close"), p.get("adjClose"), p.get("volume")
                        ))
                        prices_stored += 1
                    except:
                        continue
            
            self.conn.commit()
            progress = min(batch_start + batch_size, total)
            logger.info(f"Progress: {progress}/{total} ({100*progress/total:.1f}%) | "
                       f"Companies: {companies_stored} | Financials: {financials_stored} | Prices: {prices_stored}")
        
        return {
            "companies": companies_stored,
            "financials": financials_stored,
            "prices": prices_stored
        }
    
    async def run(self, symbols: Optional[List[str]] = None):
        """Run full ingestion."""
        start = datetime.now()
        logger.info("=" * 60)
        logger.info("FMP S&P 500 DATA INGESTION")
        logger.info("=" * 60)
        
        self.connect_db()
        self.ensure_tables()
        
        symbols = symbols or SP500_TICKERS
        logger.info(f"Symbols to process: {len(symbols)}")
        
        counts = await self.ingest_all_companies(symbols)
        
        elapsed = (datetime.now() - start).total_seconds()
        
        logger.info("=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info(f"Time: {elapsed:.1f}s ({elapsed/60:.1f} min)")
        logger.info(f"Companies: {counts['companies']}")
        logger.info(f"Financial Records: {counts['financials']}")
        logger.info(f"Price Records: {counts['prices']}")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY"))
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None, help="Limit number of symbols")
    args = parser.parse_args()
    
    if not args.api_key or not args.db_url:
        print("ERROR: FMP_API_KEY and DATABASE_URL required")
        sys.exit(1)
    
    symbols = SP500_TICKERS[:args.limit] if args.limit else None
    
    ingestor = FMPSP500Ingestor(args.api_key, args.db_url, args.concurrent)
    asyncio.run(ingestor.run(symbols))


if __name__ == "__main__":
    main()

