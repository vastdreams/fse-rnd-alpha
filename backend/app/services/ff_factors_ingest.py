"""
PATH: backend/app/services/ff_factors_ingest.py
PURPOSE:
  - Ensure Fama-French factor inputs are present in the database for spanning tests.
  - Ingest FF5 + Momentum factor data from the Ken French Data Library (ZIP CSV).

NOTES:
  - Factors are stored as DECIMAL returns (e.g., 0.01 for 1%).
  - Table: ff_factors (unique on (date, frequency)).
  - This is used by factor spanning tests and should be run rarely (cache in DB).
"""

from __future__ import annotations

import io
import zipfile
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import FamaFrenchFactor

logger = get_logger(__name__)

FF5_ZIP_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
MOM_ZIP_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"


async def get_ff_factor_counts(session: AsyncSession) -> Dict[str, int]:
    """Return row counts by frequency in ff_factors."""
    result = await session.execute(
        select(FamaFrenchFactor.frequency, func.count(FamaFrenchFactor.id))
        .group_by(FamaFrenchFactor.frequency)
        .order_by(FamaFrenchFactor.frequency)
    )
    return {str(freq): int(n) for freq, n in result.fetchall()}


async def ensure_ff_factors_populated(session: AsyncSession) -> Dict[str, Any]:
    """
    Ensure ff_factors table contains data.

    Policy:
      - If any rows exist, do nothing.
      - If empty, ingest monthly + annual FF5 and MOM datasets.
    """
    total = await session.scalar(select(func.count(FamaFrenchFactor.id)))
    if isinstance(total, int) and total > 0:
        return {"status": "ok", "note": "ff_factors already populated", "counts": await get_ff_factor_counts(session)}

    logger.info("ff_factors empty. Ingesting Fama-French factors from Ken French Data Library...")
    ingested = await ingest_ff_factors(session)
    return {"status": "ingested", **ingested}


async def _download_and_extract_zip_csv(url: str) -> str:
    """Download a ZIP file and return the contents of the first CSV file found."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        for name in z.namelist():
            if name.lower().endswith(".csv"):
                return z.read(name).decode("utf-8", errors="ignore")

    raise ValueError("No CSV found in downloaded ZIP")


def _parse_ff_csv(content: str, *, header_marker: str, frequency: str) -> pd.DataFrame:
    """
    Parse Ken French CSV content into a DataFrame for monthly or annual table.

    We detect the first header occurrence as monthly and the second as annual.
    """
    lines = content.splitlines()
    monthly_start = -1
    annual_start = -1

    for i, line in enumerate(lines):
        if header_marker in line and "," in line:
            if monthly_start == -1:
                monthly_start = i
            else:
                annual_start = i
                break

    target_start = monthly_start if frequency == "monthly" else annual_start
    if target_start == -1:
        return pd.DataFrame()

    data_lines: List[str] = []
    for i in range(target_start, len(lines)):
        line = lines[i].strip()
        if i > target_start and not line:
            break
        data_lines.append(lines[i])

    df = pd.read_csv(io.StringIO("\n".join(data_lines)))
    df.columns = [str(c).strip() for c in df.columns]
    df.rename(columns={df.columns[0]: "date_str"}, inplace=True)
    df = df[df["date_str"].astype(str).str.strip().str.isdigit()]
    return df


def _build_records(df: pd.DataFrame, *, frequency: str) -> List[Dict[str, Any]]:
    """Convert merged FF data into rows for ff_factors insert/upsert."""
    records: List[Dict[str, Any]] = []

    if df.empty:
        return records

    if frequency == "monthly":
        for _, row in df.iterrows():
            date_str = str(int(row["date_str"]))
            year = int(date_str[:4])
            month = int(date_str[4:])
            records.append(
                {
                    "date": date(year, month, 1),
                    "frequency": "monthly",
                    "mkt_rf": float(row["Mkt-RF"]) / 100.0,
                    "smb": float(row["SMB"]) / 100.0,
                    "hml": float(row["HML"]) / 100.0,
                    "rmw": float(row["RMW"]) / 100.0,
                    "cma": float(row["CMA"]) / 100.0,
                    "mom": float(row["Mom"]) / 100.0,
                    "rf": float(row["RF"]) / 100.0,
                }
            )
    else:
        for _, row in df.iterrows():
            year = int(row["date_str"])
            records.append(
                {
                    "date": date(year, 12, 31),
                    "frequency": "annual",
                    "mkt_rf": float(row["Mkt-RF"]) / 100.0,
                    "smb": float(row["SMB"]) / 100.0,
                    "hml": float(row["HML"]) / 100.0,
                    "rmw": float(row["RMW"]) / 100.0,
                    "cma": float(row["CMA"]) / 100.0,
                    "mom": float(row["Mom"]) / 100.0,
                    "rf": float(row["RF"]) / 100.0,
                }
            )

    return records


async def _upsert_records(session: AsyncSession, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    stmt = pg_insert(FamaFrenchFactor).values(rows)
    update_cols = {
        "mkt_rf": stmt.excluded.mkt_rf,
        "smb": stmt.excluded.smb,
        "hml": stmt.excluded.hml,
        "rmw": stmt.excluded.rmw,
        "cma": stmt.excluded.cma,
        "mom": stmt.excluded.mom,
        "rf": stmt.excluded.rf,
        "created_at": datetime.utcnow(),
    }
    stmt = stmt.on_conflict_do_update(index_elements=["date", "frequency"], set_=update_cols)
    result = await session.execute(stmt)

    # SQLAlchemy rowcount for upsert is not always reliable; return attempted row count.
    _ = result  # avoid lint unused
    return len(rows)


async def ingest_ff_factors(session: AsyncSession) -> Dict[str, Any]:
    """
    Ingest Ken French FF5 + MOM datasets into ff_factors as monthly and annual series.

    Returns:
      Dict with counts and a short status note.
    """
    ff5_content = await _download_and_extract_zip_csv(FF5_ZIP_URL)
    mom_content = await _download_and_extract_zip_csv(MOM_ZIP_URL)

    ff5_monthly = _parse_ff_csv(ff5_content, header_marker="Mkt-RF", frequency="monthly")
    ff5_annual = _parse_ff_csv(ff5_content, header_marker="Mkt-RF", frequency="annual")
    mom_monthly = _parse_ff_csv(mom_content, header_marker="Mom", frequency="monthly")
    mom_annual = _parse_ff_csv(mom_content, header_marker="Mom", frequency="annual")

    monthly_rows = []
    annual_rows = []

    if not ff5_monthly.empty and not mom_monthly.empty:
        monthly = pd.merge(ff5_monthly, mom_monthly, on="date_str", how="inner")
        monthly_rows = _build_records(monthly, frequency="monthly")

    if not ff5_annual.empty and not mom_annual.empty:
        annual = pd.merge(ff5_annual, mom_annual, on="date_str", how="inner")
        annual_rows = _build_records(annual, frequency="annual")

    n_monthly = await _upsert_records(session, monthly_rows)
    n_annual = await _upsert_records(session, annual_rows)
    await session.commit()

    logger.info(
        "FF factors ingestion complete",
        n_monthly=n_monthly,
        n_annual=n_annual,
    )

    return {
        "note": "FF factors ingested from Ken French Data Library (FF5 + MOM).",
        "rows_attempted": {"monthly": n_monthly, "annual": n_annual},
        "counts": await get_ff_factor_counts(session),
    }


