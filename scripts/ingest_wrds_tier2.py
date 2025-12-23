#!/usr/bin/env python3
"""
PATH: scripts/ingest_wrds_tier2.py
PURPOSE:
  - Ingest WRDS exports (CRSP/Compustat) from local files into Tier-2 stub tables
  - Strict validation of required columns and date ranges
  - Supports CSV and Parquet formats

ROLE IN ARCHITECTURE:
  - Data ingestion layer for Tier-2 (CRSP/Compustat) research pipeline
  - Populates: crsp_monthly_stock, crsp_compustat_link, compustat_annual, crsp_sp500_constituents

USAGE:
  python scripts/ingest_wrds_tier2.py --input-dir data/wrds/
  python scripts/ingest_wrds_tier2.py --validate-only  # Check files without loading

EXPECTED FILES:
  - crsp_monthly.csv (or .parquet): CRSP Monthly Stock File
  - ccm_link.csv: CRSP-Compustat Merged Link Table
  - compustat_annual.csv: Compustat Annual Fundamentals
  - crsp_sp500.csv: CRSP S&P 500 Historical Constituents

NOTES FOR FUTURE AI:
  - All ingestion is idempotent (upsert on unique keys)
  - Validation errors are actionable and specific
  - Date ranges should cover at least 1995-2024 for full analysis
"""

import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# FILE MANIFEST AND VALIDATION
# =============================================================================

FILE_MANIFEST = {
    "crsp_monthly": {
        "patterns": ["crsp_monthly.csv", "crsp_monthly.parquet", "crsp_msf.csv"],
        "required_columns": ["permno", "date", "ret"],
        "optional_columns": ["dlret", "prc", "shrout", "cfacpr", "cfacshr", "ticker", "exchcd", "shrcd"],
        "date_column": "date",
        "target_table": "crsp_monthly_stock",
        "min_year": 1990,
        "max_year": 2025,
    },
    "ccm_link": {
        "patterns": ["ccm_link.csv", "crsp_compustat_link.csv", "ccmxpf_linktable.csv"],
        "required_columns": ["permno", "gvkey"],
        "optional_columns": ["linkdt", "linkenddt", "linktype", "linkprim"],
        "date_column": "linkdt",
        "target_table": "crsp_compustat_link",
        "min_year": None,  # Link table doesn't need year validation
        "max_year": None,
    },
    "compustat_annual": {
        "patterns": ["compustat_annual.csv", "compustat_funda.csv", "funda.csv"],
        "required_columns": ["gvkey", "datadate", "fyear"],
        "optional_columns": ["xrd", "revt", "at", "ceq", "csho", "prcc_f", "ni", "oibdp", "sale", "sic", "naics"],
        "date_column": "datadate",
        "target_table": "compustat_annual",
        "min_year": 1990,
        "max_year": 2025,
    },
    "crsp_sp500": {
        "patterns": ["crsp_sp500.csv", "sp500_constituents.csv", "dsp500list.csv"],
        "required_columns": ["permno", "start"],
        "optional_columns": ["ending", "end_date", "ticker", "comnam"],
        "date_column": "start",
        "target_table": "crsp_sp500_constituents",
        "min_year": 1990,
        "max_year": 2025,
    },
}


def find_file(input_dir: Path, patterns: List[str]) -> Optional[Path]:
    """Find a file matching one of the patterns."""
    for pattern in patterns:
        path = input_dir / pattern
        if path.exists():
            return path
    return None


def load_file(path: Path) -> pd.DataFrame:
    """Load CSV or Parquet file."""
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_csv(path, low_memory=False)


def validate_columns(df: pd.DataFrame, required: List[str], optional: List[str], file_name: str) -> Tuple[bool, List[str]]:
    """Validate that required columns exist and report missing optional columns."""
    errors = []
    cols_lower = {c.lower(): c for c in df.columns}
    
    # Check required columns
    for req in required:
        if req.lower() not in cols_lower:
            errors.append(f"Missing required column '{req}' in {file_name}")
    
    # Report missing optional columns
    missing_optional = []
    for opt in optional:
        if opt.lower() not in cols_lower:
            missing_optional.append(opt)
    
    if missing_optional:
        logger.warning(f"{file_name}: Missing optional columns: {missing_optional}")
    
    return len(errors) == 0, errors


def validate_date_range(df: pd.DataFrame, date_col: str, min_year: int, max_year: int, file_name: str) -> Tuple[bool, List[str]]:
    """Validate date range coverage."""
    errors = []
    
    if date_col not in df.columns:
        # Try lowercase
        date_col_lower = date_col.lower()
        matching = [c for c in df.columns if c.lower() == date_col_lower]
        if matching:
            date_col = matching[0]
        else:
            return True, []  # Skip validation if no date column
    
    try:
        dates = pd.to_datetime(df[date_col], errors="coerce")
        years = dates.dt.year
        
        actual_min = years.min()
        actual_max = years.max()
        
        if pd.isna(actual_min) or pd.isna(actual_max):
            errors.append(f"{file_name}: Could not parse dates in '{date_col}'")
            return False, errors
        
        if actual_min > min_year + 5:
            errors.append(f"{file_name}: Data starts at {actual_min}, expected at least {min_year}")
        
        if actual_max < max_year - 5:
            errors.append(f"{file_name}: Data ends at {actual_max}, expected at least {max_year}")
        
        logger.info(f"{file_name}: Date range {actual_min}-{actual_max}")
        
    except Exception as e:
        errors.append(f"{file_name}: Error parsing dates - {e}")
    
    return len(errors) == 0, errors


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to lowercase."""
    df.columns = [c.lower() for c in df.columns]
    return df


# =============================================================================
# INGESTION FUNCTIONS
# =============================================================================

async def ingest_crsp_monthly(session: AsyncSession, df: pd.DataFrame) -> int:
    """Ingest CRSP Monthly Stock data."""
    df = normalize_columns(df)
    
    # Prepare data
    records = []
    for _, row in df.iterrows():
        record = {
            "permno": int(row["permno"]),
            "date": pd.to_datetime(row["date"]).date(),
            "ret": float(row["ret"]) if pd.notna(row.get("ret")) else None,
            "dlret": float(row["dlret"]) if pd.notna(row.get("dlret")) else None,
            "prc": float(row["prc"]) if pd.notna(row.get("prc")) else None,
            "shrout": int(row["shrout"]) if pd.notna(row.get("shrout")) else None,
            "cfacpr": float(row["cfacpr"]) if pd.notna(row.get("cfacpr")) else None,
            "cfacshr": float(row["cfacshr"]) if pd.notna(row.get("cfacshr")) else None,
            "ticker": str(row["ticker"]) if pd.notna(row.get("ticker")) else None,
            "exchcd": int(row["exchcd"]) if pd.notna(row.get("exchcd")) else None,
            "shrcd": int(row["shrcd"]) if pd.notna(row.get("shrcd")) else None,
        }
        records.append(record)
    
    # Batch insert with upsert
    if records:
        await session.execute(text("""
            INSERT INTO crsp_monthly_stock 
                (permno, date, ret, dlret, prc, shrout, cfacpr, cfacshr, ticker, exchcd, shrcd)
            VALUES 
                (:permno, :date, :ret, :dlret, :prc, :shrout, :cfacpr, :cfacshr, :ticker, :exchcd, :shrcd)
            ON CONFLICT (permno, date) DO UPDATE SET
                ret = EXCLUDED.ret,
                dlret = EXCLUDED.dlret,
                prc = EXCLUDED.prc,
                shrout = EXCLUDED.shrout,
                cfacpr = EXCLUDED.cfacpr,
                cfacshr = EXCLUDED.cfacshr,
                ticker = EXCLUDED.ticker,
                exchcd = EXCLUDED.exchcd,
                shrcd = EXCLUDED.shrcd
        """), records)
        await session.commit()
    
    return len(records)


async def ingest_ccm_link(session: AsyncSession, df: pd.DataFrame) -> int:
    """Ingest CRSP-Compustat Link data."""
    df = normalize_columns(df)
    
    records = []
    for _, row in df.iterrows():
        linkdt = pd.to_datetime(row.get("linkdt"), errors="coerce")
        linkenddt = pd.to_datetime(row.get("linkenddt"), errors="coerce")
        
        record = {
            "permno": int(row["permno"]),
            "gvkey": str(row["gvkey"]).zfill(6),  # Pad to 6 chars
            "linkdt": linkdt.date() if pd.notna(linkdt) else None,
            "linkenddt": linkenddt.date() if pd.notna(linkenddt) else None,
            "linktype": str(row["linktype"]) if pd.notna(row.get("linktype")) else None,
            "linkprim": str(row["linkprim"]) if pd.notna(row.get("linkprim")) else None,
        }
        records.append(record)
    
    # Delete existing and insert (simpler than complex upsert for link table)
    await session.execute(text("DELETE FROM crsp_compustat_link"))
    
    if records:
        await session.execute(text("""
            INSERT INTO crsp_compustat_link 
                (permno, gvkey, linkdt, linkenddt, linktype, linkprim)
            VALUES 
                (:permno, :gvkey, :linkdt, :linkenddt, :linktype, :linkprim)
        """), records)
        await session.commit()
    
    return len(records)


async def ingest_compustat_annual(session: AsyncSession, df: pd.DataFrame) -> int:
    """Ingest Compustat Annual Fundamentals."""
    df = normalize_columns(df)
    
    records = []
    for _, row in df.iterrows():
        datadate = pd.to_datetime(row["datadate"], errors="coerce")
        if pd.isna(datadate):
            continue
            
        record = {
            "gvkey": str(row["gvkey"]).zfill(6),
            "datadate": datadate.date(),
            "fyear": int(row["fyear"]),
            "xrd": float(row["xrd"]) if pd.notna(row.get("xrd")) else None,
            "revt": float(row["revt"]) if pd.notna(row.get("revt")) else None,
            "at": float(row["at"]) if pd.notna(row.get("at")) else None,
            "ceq": float(row["ceq"]) if pd.notna(row.get("ceq")) else None,
            "csho": float(row["csho"]) if pd.notna(row.get("csho")) else None,
            "prcc_f": float(row["prcc_f"]) if pd.notna(row.get("prcc_f")) else None,
            "ni": float(row["ni"]) if pd.notna(row.get("ni")) else None,
            "oibdp": float(row["oibdp"]) if pd.notna(row.get("oibdp")) else None,
            "sale": float(row["sale"]) if pd.notna(row.get("sale")) else None,
            "sic": str(row["sic"])[:4] if pd.notna(row.get("sic")) else None,
            "naics": str(row["naics"])[:6] if pd.notna(row.get("naics")) else None,
        }
        records.append(record)
    
    if records:
        await session.execute(text("""
            INSERT INTO compustat_annual 
                (gvkey, datadate, fyear, xrd, revt, at, ceq, csho, prcc_f, ni, oibdp, sale, sic, naics)
            VALUES 
                (:gvkey, :datadate, :fyear, :xrd, :revt, :at, :ceq, :csho, :prcc_f, :ni, :oibdp, :sale, :sic, :naics)
            ON CONFLICT (gvkey, datadate) DO UPDATE SET
                fyear = EXCLUDED.fyear,
                xrd = EXCLUDED.xrd,
                revt = EXCLUDED.revt,
                at = EXCLUDED.at,
                ceq = EXCLUDED.ceq,
                csho = EXCLUDED.csho,
                prcc_f = EXCLUDED.prcc_f,
                ni = EXCLUDED.ni,
                oibdp = EXCLUDED.oibdp,
                sale = EXCLUDED.sale,
                sic = EXCLUDED.sic,
                naics = EXCLUDED.naics
        """), records)
        await session.commit()
    
    return len(records)


async def ingest_crsp_sp500(session: AsyncSession, df: pd.DataFrame) -> int:
    """Ingest CRSP S&P 500 Historical Constituents."""
    df = normalize_columns(df)
    
    # Normalize column names (CRSP uses 'start'/'ending', some extracts use 'start_date'/'end_date')
    if "start" not in df.columns and "start_date" in df.columns:
        df = df.rename(columns={"start_date": "start"})
    if "ending" not in df.columns and "end_date" in df.columns:
        df = df.rename(columns={"end_date": "ending"})
    
    records = []
    for _, row in df.iterrows():
        start_date = pd.to_datetime(row["start"], errors="coerce")
        end_date = pd.to_datetime(row.get("ending"), errors="coerce")
        
        if pd.isna(start_date):
            continue
            
        record = {
            "permno": int(row["permno"]),
            "start_date": start_date.date(),
            "end_date": end_date.date() if pd.notna(end_date) else None,
            "ticker": str(row["ticker"]) if pd.notna(row.get("ticker")) else None,
            "comnam": str(row["comnam"])[:255] if pd.notna(row.get("comnam")) else None,
        }
        records.append(record)
    
    # Delete existing and insert
    await session.execute(text("DELETE FROM crsp_sp500_constituents"))
    
    if records:
        await session.execute(text("""
            INSERT INTO crsp_sp500_constituents 
                (permno, start_date, end_date, ticker, comnam)
            VALUES 
                (:permno, :start_date, :end_date, :ticker, :comnam)
        """), records)
        await session.commit()
    
    return len(records)


# =============================================================================
# MAIN
# =============================================================================

async def main(input_dir: Path, validate_only: bool = False):
    """Main ingestion function."""
    logger.info(f"WRDS Tier-2 Ingestion")
    logger.info(f"Input directory: {input_dir}")
    logger.info(f"Validate only: {validate_only}")
    
    if not input_dir.exists():
        logger.error(f"Input directory does not exist: {input_dir}")
        logger.info("Create the directory and add WRDS export files:")
        for name, spec in FILE_MANIFEST.items():
            logger.info(f"  - {spec['patterns'][0]} ({name})")
        sys.exit(1)
    
    # Find and validate files
    all_errors = []
    files_found = {}
    
    for name, spec in FILE_MANIFEST.items():
        path = find_file(input_dir, spec["patterns"])
        
        if path is None:
            logger.warning(f"File not found for {name}: tried {spec['patterns']}")
            continue
        
        logger.info(f"Found {name}: {path}")
        files_found[name] = path
        
        # Load and validate
        try:
            df = load_file(path)
            logger.info(f"  Loaded {len(df):,} rows, {len(df.columns)} columns")
            
            # Validate columns
            valid, errors = validate_columns(df, spec["required_columns"], spec["optional_columns"], name)
            all_errors.extend(errors)
            
            # Validate date range
            if spec["min_year"] and spec["max_year"]:
                valid, errors = validate_date_range(df, spec["date_column"], spec["min_year"], spec["max_year"], name)
                all_errors.extend(errors)
            
        except Exception as e:
            all_errors.append(f"Error loading {name}: {e}")
    
    # Report validation results
    if all_errors:
        logger.error("Validation failed with the following errors:")
        for error in all_errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    if not files_found:
        logger.error("No WRDS files found in input directory")
        logger.info("Expected files:")
        for name, spec in FILE_MANIFEST.items():
            logger.info(f"  - {spec['patterns'][0]}")
        sys.exit(1)
    
    if validate_only:
        logger.info("Validation passed. Use without --validate-only to ingest.")
        return
    
    # Ingest data
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            ingest_funcs = {
                "crsp_monthly": ingest_crsp_monthly,
                "ccm_link": ingest_ccm_link,
                "compustat_annual": ingest_compustat_annual,
                "crsp_sp500": ingest_crsp_sp500,
            }
            
            for name, path in files_found.items():
                if name in ingest_funcs:
                    logger.info(f"Ingesting {name}...")
                    df = load_file(path)
                    count = await ingest_funcs[name](session, df)
                    logger.info(f"  Ingested {count:,} records into {FILE_MANIFEST[name]['target_table']}")
            
            logger.info("Tier-2 ingestion complete!")
            
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest WRDS exports into Tier-2 tables")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("data/wrds"),
        help="Directory containing WRDS export files (default: data/wrds)"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate files without ingesting"
    )
    
    args = parser.parse_args()
    asyncio.run(main(args.input_dir, args.validate_only))

