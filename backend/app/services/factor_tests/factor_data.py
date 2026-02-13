"""
PATH: backend/app/services/factor_tests/factor_data.py
PURPOSE: Mixin providing Fama-French factor data retrieval from database
WHY: Factor data fetching is shared across annual and monthly spanning tests
DEPENDENCIES:
  - sqlalchemy: database queries
  - app.db.models.FamaFrenchFactor: factor data table
"""

from typing import Dict, List, Optional
from datetime import date

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FamaFrenchFactor


class FactorDataMixin:
    """Mixin providing methods to fetch Fama-French factor data."""

    session: AsyncSession  # Set by the concrete class

    async def get_ff_factors_calendar(
        self,
        start_year: int,
        end_year: int,
        frequency: str = "annual"
    ) -> Dict[int, Dict[str, float]]:
        """
        Get Fama-French factors from database.

        Returns dict: year -> {mkt_rf, smb, hml, rmw, cma, mom, rf}
        """
        result = await self.session.execute(
            select(FamaFrenchFactor)
            .where(
                FamaFrenchFactor.frequency == frequency,
                func.extract("year", FamaFrenchFactor.date) >= start_year,
                func.extract("year", FamaFrenchFactor.date) <= end_year
            )
            .order_by(FamaFrenchFactor.date)
        )
        rows = result.scalars().all()

        factors = {}
        for r in rows:
            year = r.date.year
            factors[year] = {
                "mkt_rf": r.mkt_rf,
                "smb": r.smb,
                "hml": r.hml,
                "rmw": r.rmw,
                "cma": r.cma,
                "mom": r.mom,
                "rf": r.rf
            }

        return factors

    async def get_ff_factors_july_june(
        self,
        start_year: int,
        end_year: int,
    ) -> Dict[int, Dict[str, float]]:
        """
        Build July-June annual factor returns by compounding monthly FF factors.

        Alignment:
          - For return year label Y (July Y -> June Y+1), we compound months:
              Jul(Y), Aug(Y), ..., Dec(Y), Jan(Y+1), ..., Jun(Y+1)

        Returns dict: return_year_start -> {mkt_rf, smb, hml, rmw, cma, mom, rf}
        """
        start_date = date(int(start_year), 7, 1)
        end_date = date(int(end_year) + 1, 6, 1)

        result = await self.session.execute(
            select(FamaFrenchFactor)
            .where(
                FamaFrenchFactor.frequency == "monthly",
                FamaFrenchFactor.date >= start_date,
                FamaFrenchFactor.date <= end_date,
            )
            .order_by(FamaFrenchFactor.date)
        )
        rows = result.scalars().all()

        buckets: Dict[int, Dict[str, List[float]]] = {}
        keys = ["mkt_rf", "smb", "hml", "rmw", "cma", "mom", "rf"]

        for r in rows:
            y = int(r.date.year) if int(r.date.month) >= 7 else int(r.date.year) - 1
            if y < start_year or y > end_year:
                continue

            if y not in buckets:
                buckets[y] = {k: [] for k in keys}

            for k in keys:
                v = getattr(r, k, None)
                if v is None:
                    # Missing factor data in a required month -> skip year later
                    buckets[y][k].append(np.nan)
                else:
                    buckets[y][k].append(float(v))

        def compound(xs: List[float]) -> Optional[float]:
            arr = np.array(xs, dtype=float)
            if len(arr) != 12:
                return None
            if not np.isfinite(arr).all():
                return None
            return float(np.prod(1.0 + arr) - 1.0)

        factors: Dict[int, Dict[str, float]] = {}
        for y, series in buckets.items():
            out: Dict[str, float] = {}
            ok = True
            for k in keys:
                c = compound(series.get(k, []))
                if c is None:
                    ok = False
                    break
                out[k] = c
            if ok:
                factors[int(y)] = out

        return factors
