#!/usr/bin/env python
"""
PATH: scripts/ingest_fmp_bulk.py
PURPOSE:
  - Bulk ingestion of financial data from Financial Modeling Prep (FMP) API.
  - Fetches 30+ years of data for 500+ S&P 500 companies.
  - Optimized for maximum concurrency.

ROLE IN ARCHITECTURE:
  - Data ingestion script for research database population.

MAIN EXPORTS:
  - CLI script for bulk data ingestion.

NON-RESPONSIBILITIES:
  - Does not compute derived factors (use separate scripts after ingestion).

NOTES FOR FUTURE AI:
  - FMP bulk endpoints return all companies at once per year.
  - Total API calls = ~31 years x 3 statement types + 500 price calls = ~600 calls.
  - With parallel execution: ~10-15 minutes total.
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Any, Optional
import logging

# Setup path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database imports
import psycopg2
from psycopg2.extras import execute_values

# FMP Client
sys.path.insert(0, str(ROOT / "backend"))
from app.services.fmp_client import FMPClient


class FMPBulkIngestor:
    """
    Bulk data ingestor using FMP API.
    
    Fetches and stores financial statements, metrics, and prices
    for S&P 500 companies across 30+ years.
    """
    
    def __init__(
        self,
        api_key: str,
        db_url: str,
        start_year: int = 1995,
        end_year: int = 2025
    ):
        """
        Initialize ingestor.
        
        Args:
            api_key: FMP API key.
            db_url: PostgreSQL connection URL.
            start_year: First year to fetch.
            end_year: Last year to fetch.
        """
        self.api_key = api_key
        self.db_url = db_url
        self.start_year = start_year
        self.end_year = end_year
        self.conn = None
        
    def connect_db(self):
        """Establish database connection."""
        # Parse connection string
        # Format: postgresql://user:pass@host:port/dbname
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
    
    def close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
    
    def ensure_tables(self):
        """Create required database tables if they don't exist."""
        cursor = self.conn.cursor()
        
        # FMP Companies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_companies (
                symbol VARCHAR(20) PRIMARY KEY,
                name VARCHAR(255),
                sector VARCHAR(100),
                sub_sector VARCHAR(100),
                cik VARCHAR(20),
                exchange VARCHAR(50),
                founded VARCHAR(20),
                ipo_date DATE,
                is_sp500 BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # FMP Income Statements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_income_statements (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                fiscal_period VARCHAR(10),
                date DATE,
                revenue NUMERIC,
                cost_of_revenue NUMERIC,
                gross_profit NUMERIC,
                rd_expenses NUMERIC,
                sga_expenses NUMERIC,
                operating_expenses NUMERIC,
                operating_income NUMERIC,
                interest_expense NUMERIC,
                income_before_tax NUMERIC,
                income_tax_expense NUMERIC,
                net_income NUMERIC,
                eps NUMERIC,
                eps_diluted NUMERIC,
                shares_outstanding BIGINT,
                shares_outstanding_diluted BIGINT,
                ebitda NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fiscal_year, fiscal_period)
            )
        """)
        
        # FMP Balance Sheets
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_balance_sheets (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                fiscal_period VARCHAR(10),
                date DATE,
                cash_and_equivalents NUMERIC,
                short_term_investments NUMERIC,
                total_current_assets NUMERIC,
                property_plant_equipment NUMERIC,
                goodwill NUMERIC,
                intangible_assets NUMERIC,
                total_assets NUMERIC,
                accounts_payable NUMERIC,
                short_term_debt NUMERIC,
                total_current_liabilities NUMERIC,
                long_term_debt NUMERIC,
                total_liabilities NUMERIC,
                total_stockholders_equity NUMERIC,
                retained_earnings NUMERIC,
                common_stock NUMERIC,
                total_debt NUMERIC,
                net_debt NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fiscal_year, fiscal_period)
            )
        """)
        
        # FMP Cash Flows
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_cash_flows (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                fiscal_period VARCHAR(10),
                date DATE,
                net_income NUMERIC,
                depreciation_amortization NUMERIC,
                stock_based_compensation NUMERIC,
                operating_cash_flow NUMERIC,
                capital_expenditure NUMERIC,
                acquisitions NUMERIC,
                investing_cash_flow NUMERIC,
                debt_repayment NUMERIC,
                dividends_paid NUMERIC,
                stock_repurchased NUMERIC,
                financing_cash_flow NUMERIC,
                free_cash_flow NUMERIC,
                net_change_in_cash NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fiscal_year, fiscal_period)
            )
        """)
        
        # Stock Prices (Daily)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_stock_prices (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                date DATE,
                open NUMERIC,
                high NUMERIC,
                low NUMERIC,
                close NUMERIC,
                adj_close NUMERIC,
                volume BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        
        # Annual Returns (computed)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_annual_returns (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                year INT,
                annual_return NUMERIC,
                annual_volatility NUMERIC,
                start_price NUMERIC,
                end_price NUMERIC,
                high_price NUMERIC,
                low_price NUMERIC,
                avg_volume BIGINT,
                trading_days INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, year)
            )
        """)
        
        # Key Metrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fmp_key_metrics (
                id SERIAL PRIMARY KEY,
                symbol VARCHAR(20),
                fiscal_year INT,
                fiscal_period VARCHAR(10),
                date DATE,
                revenue_per_share NUMERIC,
                net_income_per_share NUMERIC,
                operating_cash_flow_per_share NUMERIC,
                free_cash_flow_per_share NUMERIC,
                book_value_per_share NUMERIC,
                tangible_book_value_per_share NUMERIC,
                pe_ratio NUMERIC,
                price_to_sales NUMERIC,
                price_to_book NUMERIC,
                price_to_free_cash_flow NUMERIC,
                enterprise_value NUMERIC,
                ev_to_sales NUMERIC,
                ev_to_ebitda NUMERIC,
                roe NUMERIC,
                roa NUMERIC,
                roic NUMERIC,
                current_ratio NUMERIC,
                quick_ratio NUMERIC,
                debt_to_equity NUMERIC,
                debt_to_assets NUMERIC,
                dividend_yield NUMERIC,
                payout_ratio NUMERIC,
                rd_to_revenue NUMERIC,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, fiscal_year, fiscal_period)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_income_symbol ON fmp_income_statements(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_income_year ON fmp_income_statements(fiscal_year)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_balance_symbol ON fmp_balance_sheets(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_cashflow_symbol ON fmp_cash_flows(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_prices_symbol ON fmp_stock_prices(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_prices_date ON fmp_stock_prices(date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fmp_returns_symbol ON fmp_annual_returns(symbol)")
        
        self.conn.commit()
        logger.info("Database tables ensured")
    
    async def fetch_and_store_sp500(self):
        """Fetch and store S&P 500 constituents."""
        async with FMPClient(self.api_key) as client:
            companies = await client.get_sp500_constituents()
        
        if not companies:
            logger.error("Failed to fetch S&P 500 constituents")
            return []
        
        cursor = self.conn.cursor()
        
        for company in companies:
            cursor.execute("""
                INSERT INTO fmp_companies (symbol, name, sector, sub_sector, cik, exchange, founded, is_sp500)
                VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                ON CONFLICT (symbol) DO UPDATE SET
                    name = EXCLUDED.name,
                    sector = EXCLUDED.sector,
                    sub_sector = EXCLUDED.sub_sector,
                    cik = EXCLUDED.cik,
                    is_sp500 = TRUE,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                company.get("symbol"),
                company.get("name"),
                company.get("sector"),
                company.get("subSector"),
                company.get("cik"),
                company.get("exchange"),
                company.get("founded"),
            ))
        
        self.conn.commit()
        logger.info(f"Stored {len(companies)} S&P 500 companies")
        
        return [c.get("symbol") for c in companies]
    
    async def fetch_and_store_financials(self):
        """Fetch and store all financial statements for all years."""
        async with FMPClient(self.api_key) as client:
            all_data = await client.fetch_all_years_financials(
                start_year=self.start_year,
                end_year=self.end_year,
                max_concurrent=15
            )
        
        cursor = self.conn.cursor()
        
        # Store income statements
        income_count = 0
        for record in all_data.get("income_statements", []):
            try:
                # Parse date to get fiscal year
                date_str = record.get("date") or record.get("fillingDate")
                if not date_str:
                    continue
                
                fiscal_year = int(date_str[:4]) if date_str else None
                
                cursor.execute("""
                    INSERT INTO fmp_income_statements 
                    (symbol, fiscal_year, fiscal_period, date, revenue, cost_of_revenue,
                     gross_profit, rd_expenses, sga_expenses, operating_expenses,
                     operating_income, interest_expense, income_before_tax,
                     income_tax_expense, net_income, eps, eps_diluted,
                     shares_outstanding, shares_outstanding_diluted, ebitda)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, fiscal_year, fiscal_period) DO UPDATE SET
                        revenue = EXCLUDED.revenue,
                        rd_expenses = EXCLUDED.rd_expenses,
                        net_income = EXCLUDED.net_income,
                        ebitda = EXCLUDED.ebitda
                """, (
                    record.get("symbol"),
                    fiscal_year,
                    record.get("period", "FY"),
                    date_str,
                    record.get("revenue"),
                    record.get("costOfRevenue"),
                    record.get("grossProfit"),
                    record.get("researchAndDevelopmentExpenses"),
                    record.get("sellingGeneralAndAdministrativeExpenses"),
                    record.get("operatingExpenses"),
                    record.get("operatingIncome"),
                    record.get("interestExpense"),
                    record.get("incomeBeforeTax"),
                    record.get("incomeTaxExpense"),
                    record.get("netIncome"),
                    record.get("eps"),
                    record.get("epsdiluted"),
                    record.get("weightedAverageShsOut"),
                    record.get("weightedAverageShsOutDil"),
                    record.get("ebitda"),
                ))
                income_count += 1
            except Exception as e:
                logger.debug(f"Income statement insert error: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Stored {income_count} income statements")
        
        # Store balance sheets
        balance_count = 0
        for record in all_data.get("balance_sheets", []):
            try:
                date_str = record.get("date") or record.get("fillingDate")
                if not date_str:
                    continue
                
                fiscal_year = int(date_str[:4]) if date_str else None
                
                cursor.execute("""
                    INSERT INTO fmp_balance_sheets
                    (symbol, fiscal_year, fiscal_period, date, cash_and_equivalents,
                     short_term_investments, total_current_assets, property_plant_equipment,
                     goodwill, intangible_assets, total_assets, accounts_payable,
                     short_term_debt, total_current_liabilities, long_term_debt,
                     total_liabilities, total_stockholders_equity, retained_earnings,
                     common_stock, total_debt, net_debt)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, fiscal_year, fiscal_period) DO UPDATE SET
                        total_assets = EXCLUDED.total_assets,
                        total_liabilities = EXCLUDED.total_liabilities,
                        total_stockholders_equity = EXCLUDED.total_stockholders_equity
                """, (
                    record.get("symbol"),
                    fiscal_year,
                    record.get("period", "FY"),
                    date_str,
                    record.get("cashAndCashEquivalents"),
                    record.get("shortTermInvestments"),
                    record.get("totalCurrentAssets"),
                    record.get("propertyPlantEquipmentNet"),
                    record.get("goodwill"),
                    record.get("intangibleAssets"),
                    record.get("totalAssets"),
                    record.get("accountPayables"),
                    record.get("shortTermDebt"),
                    record.get("totalCurrentLiabilities"),
                    record.get("longTermDebt"),
                    record.get("totalLiabilities"),
                    record.get("totalStockholdersEquity"),
                    record.get("retainedEarnings"),
                    record.get("commonStock"),
                    record.get("totalDebt"),
                    record.get("netDebt"),
                ))
                balance_count += 1
            except Exception as e:
                logger.debug(f"Balance sheet insert error: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Stored {balance_count} balance sheets")
        
        # Store cash flows
        cashflow_count = 0
        for record in all_data.get("cash_flows", []):
            try:
                date_str = record.get("date") or record.get("fillingDate")
                if not date_str:
                    continue
                
                fiscal_year = int(date_str[:4]) if date_str else None
                
                cursor.execute("""
                    INSERT INTO fmp_cash_flows
                    (symbol, fiscal_year, fiscal_period, date, net_income,
                     depreciation_amortization, stock_based_compensation,
                     operating_cash_flow, capital_expenditure, acquisitions,
                     investing_cash_flow, debt_repayment, dividends_paid,
                     stock_repurchased, financing_cash_flow, free_cash_flow,
                     net_change_in_cash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, fiscal_year, fiscal_period) DO UPDATE SET
                        operating_cash_flow = EXCLUDED.operating_cash_flow,
                        free_cash_flow = EXCLUDED.free_cash_flow
                """, (
                    record.get("symbol"),
                    fiscal_year,
                    record.get("period", "FY"),
                    date_str,
                    record.get("netIncome"),
                    record.get("depreciationAndAmortization"),
                    record.get("stockBasedCompensation"),
                    record.get("operatingCashFlow"),
                    record.get("capitalExpenditure"),
                    record.get("acquisitionsNet"),
                    record.get("investmentsInPropertyPlantAndEquipment"),
                    record.get("debtRepayment"),
                    record.get("dividendsPaid"),
                    record.get("commonStockRepurchased"),
                    record.get("netCashUsedProvidedByFinancingActivities"),
                    record.get("freeCashFlow"),
                    record.get("netChangeInCash"),
                ))
                cashflow_count += 1
            except Exception as e:
                logger.debug(f"Cash flow insert error: {e}")
                continue
        
        self.conn.commit()
        logger.info(f"Stored {cashflow_count} cash flow statements")
        
        return {
            "income_statements": income_count,
            "balance_sheets": balance_count,
            "cash_flows": cashflow_count
        }
    
    async def fetch_and_store_prices(self, symbols: List[str], batch_size: int = 50):
        """
        Fetch and store historical prices for all symbols.
        
        Args:
            symbols: List of stock symbols.
            batch_size: Number of symbols to process in each batch.
        """
        cursor = self.conn.cursor()
        total_records = 0
        
        # Process in batches
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            logger.info(f"Fetching prices for symbols {i+1}-{i+len(batch)} of {len(symbols)}")
            
            async with FMPClient(self.api_key) as client:
                prices_data = await client.fetch_prices_for_symbols(
                    batch,
                    from_date=f"{self.start_year}-01-01",
                    max_concurrent=20
                )
            
            # Store prices
            for symbol, prices in prices_data.items():
                if not prices:
                    continue
                
                for record in prices:
                    try:
                        cursor.execute("""
                            INSERT INTO fmp_stock_prices
                            (symbol, date, open, high, low, close, adj_close, volume)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, date) DO NOTHING
                        """, (
                            symbol,
                            record.get("date"),
                            record.get("open"),
                            record.get("high"),
                            record.get("low"),
                            record.get("close"),
                            record.get("adjClose"),
                            record.get("volume"),
                        ))
                        total_records += 1
                    except Exception as e:
                        logger.debug(f"Price insert error: {e}")
                        continue
            
            self.conn.commit()
            logger.info(f"Batch complete. Total price records: {total_records}")
        
        logger.info(f"Stored {total_records} total price records")
        return total_records
    
    def compute_annual_returns(self):
        """Compute annual returns from daily prices."""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO fmp_annual_returns (symbol, year, annual_return, annual_volatility,
                start_price, end_price, high_price, low_price, avg_volume, trading_days)
            SELECT 
                symbol,
                EXTRACT(YEAR FROM date)::INT as year,
                (MAX(CASE WHEN date = max_date THEN adj_close END) / 
                 NULLIF(MAX(CASE WHEN date = min_date THEN adj_close END), 0) - 1) as annual_return,
                STDDEV(daily_return) * SQRT(252) as annual_volatility,
                MAX(CASE WHEN date = min_date THEN adj_close END) as start_price,
                MAX(CASE WHEN date = max_date THEN adj_close END) as end_price,
                MAX(high) as high_price,
                MIN(low) as low_price,
                AVG(volume)::BIGINT as avg_volume,
                COUNT(*) as trading_days
            FROM (
                SELECT 
                    p.*,
                    (adj_close / NULLIF(LAG(adj_close) OVER (PARTITION BY symbol ORDER BY date), 0) - 1) as daily_return,
                    MIN(date) OVER (PARTITION BY symbol, EXTRACT(YEAR FROM date)) as min_date,
                    MAX(date) OVER (PARTITION BY symbol, EXTRACT(YEAR FROM date)) as max_date
                FROM fmp_stock_prices p
            ) sub
            GROUP BY symbol, EXTRACT(YEAR FROM date)
            ON CONFLICT (symbol, year) DO UPDATE SET
                annual_return = EXCLUDED.annual_return,
                annual_volatility = EXCLUDED.annual_volatility
        """)
        
        self.conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM fmp_annual_returns")
        count = cursor.fetchone()[0]
        logger.info(f"Computed {count} annual return records")
        return count
    
    async def run_full_ingestion(self):
        """Run complete data ingestion pipeline."""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("FMP BULK DATA INGESTION")
        logger.info(f"Period: {self.start_year} - {self.end_year}")
        logger.info("=" * 60)
        
        # Connect and setup
        self.connect_db()
        self.ensure_tables()
        
        # Step 1: Fetch S&P 500 constituents
        logger.info("\n[1/4] Fetching S&P 500 constituents...")
        symbols = await self.fetch_and_store_sp500()
        
        if not symbols:
            logger.error("No symbols found. Aborting.")
            return
        
        # Step 2: Fetch all financial statements
        logger.info("\n[2/4] Fetching financial statements (all years in parallel)...")
        financial_counts = await self.fetch_and_store_financials()
        
        # Step 3: Fetch historical prices
        logger.info("\n[3/4] Fetching historical prices...")
        price_count = await self.fetch_and_store_prices(symbols)
        
        # Step 4: Compute returns
        logger.info("\n[4/4] Computing annual returns...")
        return_count = self.compute_annual_returns()
        
        # Summary
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        logger.info(f"Companies: {len(symbols)}")
        logger.info(f"Income Statements: {financial_counts.get('income_statements', 0)}")
        logger.info(f"Balance Sheets: {financial_counts.get('balance_sheets', 0)}")
        logger.info(f"Cash Flow Statements: {financial_counts.get('cash_flows', 0)}")
        logger.info(f"Stock Price Records: {price_count}")
        logger.info(f"Annual Returns: {return_count}")
        logger.info("=" * 60)
        
        self.close_db()


def main():
    parser = argparse.ArgumentParser(description="FMP Bulk Data Ingestion")
    parser.add_argument("--api-key", default=os.environ.get("FMP_API_KEY"),
                        help="FMP API key")
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL"),
                        help="PostgreSQL connection URL")
    parser.add_argument("--start-year", type=int, default=1995,
                        help="Start year for data (default: 1995)")
    parser.add_argument("--end-year", type=int, default=2025,
                        help="End year for data (default: 2025)")
    parser.add_argument("--test", action="store_true",
                        help="Test FMP connection only")
    
    args = parser.parse_args()
    
    if not args.api_key:
        print("ERROR: FMP API key required. Set FMP_API_KEY or use --api-key")
        sys.exit(1)
    
    if not args.db_url:
        print("ERROR: Database URL required. Set DATABASE_URL or use --db-url")
        sys.exit(1)
    
    if args.test:
        from app.services.fmp_client import test_fmp_connection
        result = asyncio.run(test_fmp_connection(args.api_key))
        print(f"Connection test: {'OK' if result else 'FAILED'}")
        sys.exit(0 if result else 1)
    
    ingestor = FMPBulkIngestor(
        api_key=args.api_key,
        db_url=args.db_url,
        start_year=args.start_year,
        end_year=args.end_year
    )
    
    asyncio.run(ingestor.run_full_ingestion())


if __name__ == "__main__":
    main()

