#!/usr/bin/env python3
"""
PATH: scripts/ingest_risk_free_rates.py
PURPOSE:
  - Extract Risk-Free Rate data from Ken French Data Library
  - Populate risk_free_rates table for Sharpe ratio calculations
"""

import asyncio
import io
import logging
import sys
import zipfile
from datetime import datetime, date
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
from app.db.models import RiskFreeRate, Base

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

FF3_ZIP_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"

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

def parse_rf_csv(content: str) -> pd.DataFrame:
    """Parse Ken French CSV content to extract RF."""
    lines = content.splitlines()
    
    # Find start of monthly table
    monthly_start = -1
    for i, line in enumerate(lines):
        if "Mkt-RF" in line and "SMB" in line and "HML" in line and "RF" in line:
            monthly_start = i
            break
            
    if monthly_start == -1:
        return pd.DataFrame()
        
    # Read until blank line
    data_lines = []
    for i in range(monthly_start, len(lines)):
        line = lines[i].strip()
        if i > monthly_start and not line:
            break
        data_lines.append(lines[i])
        
    df = pd.read_csv(io.StringIO("\n".join(data_lines)))
    df.columns = [c.strip() for c in df.columns]
    df.rename(columns={df.columns[0]: "date_str"}, inplace=True)
    df = df[df["date_str"].astype(str).str.strip().str.isdigit()]
    
    return df[["date_str", "RF"]]

async def ingest_rf_data():
    """Download, parse, and ingest RF data."""
    engine = create_async_engine(settings.async_database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        content = await download_and_extract_zip(FF3_ZIP_URL)
        df = parse_rf_csv(content)
        
        if df.empty:
            logger.error("Could not parse RF data from CSV")
            return
            
        async with async_session() as session:
            logger.info(f"Ingesting {len(df)} risk-free rate records...")
            for _, row in df.iterrows():
                date_str = str(int(row["date_str"]))
                year = int(date_str[:4])
                month = int(date_str[4:])
                date_val = date(year, month, 1)
                
                # RF in Ken French files is monthly rate in percent
                # e.g., 0.26 means 0.26% for the month
                monthly_rate_pct = float(row["RF"])
                # Annualized percentage (roughly monthly * 12)
                annual_rate_pct = monthly_rate_pct * 12
                
                rf = RiskFreeRate(
                    date=date_val,
                    rate_annual_pct=annual_rate_pct,
                    rate_monthly=monthly_rate_pct / 100,  # as decimal
                    source='FF_RF'
                )
                await session.merge(rf)
            
            await session.commit()
            logger.info("Risk-free rate ingestion complete.")
            
    except Exception as e:
        logger.error(f"Error ingesting risk-free rates: {e}")
        await session.rollback()
        raise
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(ingest_rf_data())

