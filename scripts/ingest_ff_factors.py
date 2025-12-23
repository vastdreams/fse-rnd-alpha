#!/usr/bin/env python3
"""
PATH: scripts/ingest_ff_factors.py
PURPOSE:
  - Download and parse Fama-French factor data from Ken French Data Library
  - Populate ff_factors table with monthly and annual data
  - Supports MKT-RF, SMB, HML, RMW, CMA, and MOM factors

ROLE IN ARCHITECTURE:
  - Data ingestion script for research verification
  - Provides benchmark factors for spanning tests
"""

import asyncio
import io
import logging
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import httpx
import pandas as pd
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.db.models import FamaFrenchFactor, RiskFreeRate, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

FF5_ZIP_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
MOM_ZIP_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"

async def download_and_extract_zip(url: str) -> str:
    """Download a ZIP file and return the contents of the first CSV file found."""
    logger.info(f"Downloading {url}...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
    
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        for name in z.namelist():
            if name.endswith(".csv") or name.endswith(".CSV"):
                logger.info(f"Extracting {name}...")
                return z.read(name).decode("utf-8", errors="ignore")
    
    raise ValueError(f"No CSV file found in {url}")

def parse_ff_csv(content: str, factor_type: str = "ff5", frequency: str = "monthly") -> pd.DataFrame:
    """Parse Ken French CSV content into a DataFrame."""
    lines = content.splitlines()
    
    # Find start indices for monthly and annual tables
    monthly_start = -1
    annual_start = -1
    
    header_marker = "Mkt-RF" if factor_type == "ff5" else "Mom"
    
    for i, line in enumerate(lines):
        if header_marker in line and "," in line:
            if monthly_start == -1:
                monthly_start = i
            else:
                annual_start = i
                break
                
    target_start = monthly_start if frequency == "monthly" else annual_start
    
    if target_start == -1:
        logger.warning(f"Could not find {frequency} table for {factor_type}")
        return pd.DataFrame()
        
    # Read until next blank line or end
    data_lines = []
    for i in range(target_start, len(lines)):
        line = lines[i].strip()
        if i > target_start and not line:
            break
        data_lines.append(lines[i])
        
    df = pd.read_csv(io.StringIO("\n".join(data_lines)))
    
    # Clean up column names
    df.columns = [c.strip() for c in df.columns]
    # Rename first column to 'date_str'
    df.rename(columns={df.columns[0]: "date_str"}, inplace=True)
    
    # Filter out non-numeric dates
    df = df[df["date_str"].astype(str).str.strip().str.isdigit()]
    
    return df

async def ingest_ff_data():
    """Download, parse, and ingest FF factors."""
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        # 1. Get FF5 data
        ff5_content = await download_and_extract_zip(FF5_ZIP_URL)
        ff5_monthly = parse_ff_csv(ff5_content, "ff5", "monthly")
        ff5_annual = parse_ff_csv(ff5_content, "ff5", "annual")
        
        # 2. Get MOM data
        mom_content = await download_and_extract_zip(MOM_ZIP_URL)
        mom_monthly = parse_ff_csv(mom_content, "mom", "monthly")
        mom_annual = parse_ff_csv(mom_content, "mom", "annual")
        
        # 3. Merge and ingest
        async with async_session() as session:
            # Monthly Ingestion
            if not ff5_monthly.empty and not mom_monthly.empty:
                monthly = pd.merge(ff5_monthly, mom_monthly, on="date_str", how="inner")
                logger.info(f"Ingesting {len(monthly)} monthly records...")
                for _, row in monthly.iterrows():
                    date_str = str(int(row["date_str"]))
                    year = int(date_str[:4])
                    month = int(date_str[4:])
                    date_val = datetime(year, month, 1).date()
                    
                    f = FamaFrenchFactor(
                        date=date_val,
                        frequency="monthly",
                        mkt_rf=float(row["Mkt-RF"]) / 100,
                        smb=float(row["SMB"]) / 100,
                        hml=float(row["HML"]) / 100,
                        rmw=float(row["RMW"]) / 100,
                        cma=float(row["CMA"]) / 100,
                        mom=float(row["Mom"]) / 100,
                        rf=float(row["RF"]) / 100
                    )
                    await session.merge(f)
            
            # Annual Ingestion
            if not ff5_annual.empty and not mom_annual.empty:
                annual = pd.merge(ff5_annual, mom_annual, on="date_str", how="inner")
                logger.info(f"Ingesting {len(annual)} annual records...")
                for _, row in annual.iterrows():
                    year = int(row["date_str"])
                    date_val = datetime(year, 12, 31).date()
                    
                    f = FamaFrenchFactor(
                        date=date_val,
                        frequency="annual",
                        mkt_rf=float(row["Mkt-RF"]) / 100,
                        smb=float(row["SMB"]) / 100,
                        hml=float(row["HML"]) / 100,
                        rmw=float(row["RMW"]) / 100,
                        cma=float(row["CMA"]) / 100,
                        mom=float(row["Mom"]) / 100,
                        rf=float(row["RF"]) / 100
                    )
                    await session.merge(f)
            
            # Also populate RiskFreeRate table from RF data
            if not ff5_monthly.empty:
                logger.info("Populating RiskFreeRate table from RF data...")
                rf_count = 0
                for _, row in ff5_monthly.iterrows():
                    try:
                        date_str = str(int(row["date_str"]))
                        year = int(date_str[:4])
                        month = int(date_str[4:])
                        date_val = datetime(year, month, 1).date()
                        rf_monthly = float(row["RF"])  # Monthly percentage
                        rf_annual = rf_monthly * 12  # Annualize (approximate)
                        
                        rf_entry = RiskFreeRate(
                            date=date_val,
                            rate_annual_pct=rf_annual,
                            rate_monthly=rf_monthly / 100,  # Convert to decimal
                            source="FF_RF"
                        )
                        await session.merge(rf_entry)
                        rf_count += 1
                    except Exception as e:
                        logger.warning(f"Error parsing RF row: {e}")
                        continue
                
                logger.info(f"Ingested {rf_count} risk-free rate records")
            
            await session.commit()
            logger.info("FF factor and risk-free rate ingestion complete successfully.")
            
    except Exception as e:
        logger.error(f"Error ingesting FF factors: {e}")
        await session.rollback()
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(ingest_ff_data())

