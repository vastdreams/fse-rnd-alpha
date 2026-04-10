"""
PATH: backend/app/services/pnl_efficiency_scorer/scorer.py
PURPOSE: Core PNL Efficiency Alpha scoring engine.

Computes sector-relative operating-efficiency scores from structured
FMP income-statement data. Uses the same point-in-time and July-June
timing discipline as RDAlphaScorer.

DOES NOT USE: payroll, employee count, or any annual-report-extracted field.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from statistics import mean, stdev

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FMPIncomeStatement, SP500Company
from app.services.sanity_checks import MIN_REVENUE_THRESHOLD
from app.core.logging import get_logger

from app.services.pnl_efficiency_scorer.data_classes import PnlEfficiencyScore

logger = get_logger(__name__)

WINSORIZE_LIMIT = 3.0
MIN_SECTOR_SIZE = 5


class PnlEfficiencyScorer:
    """
    Sector-relative P&L efficiency scoring engine.

    Score = equal-weight average of four sector-year z-scored components:
      1. Gross Efficiency   = 1 - (COGS / Revenue)
      2. Overhead Efficiency = 1 - (SGA / Revenue)
      3. Operating Efficiency = 1 - (OpEx / Revenue)
      4. Profit Conversion  = Net Income / Revenue

    Higher composite z-score = more operationally efficient vs sector peers.
    """

    MAX_SECTOR_WEIGHT = 0.25
    MIN_SECTOR_WEIGHT = 0.02

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_scores(
        self,
        as_of_year: Optional[int] = None,
        min_revenue: float = MIN_REVENUE_THRESHOLD,
    ) -> List[PnlEfficiencyScore]:
        """
        Calculate PNL Efficiency scores for all S&P 500 companies.

        Uses FY(T-1) data when as_of_year is provided (point-in-time).
        """
        start_time = time.perf_counter()
        data_year = (as_of_year - 1) if as_of_year else None

        raw_rows = await self._fetch_financials(data_year, min_revenue)
        if not raw_rows:
            logger.warning("No financials found for PNL scoring")
            return []

        by_sector: Dict[str, List[dict]] = {}
        for row in raw_rows:
            by_sector.setdefault(row["sector"], []).append(row)

        scores: List[PnlEfficiencyScore] = []

        for sector, companies in by_sector.items():
            if len(companies) < MIN_SECTOR_SIZE:
                continue
            sector_scores = self._score_sector(companies, sector)
            scores.extend(sector_scores)

        scores.sort(key=lambda s: s.final_score, reverse=True)
        for i, s in enumerate(scores):
            s.selection_rank = i + 1

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"PNL scores computed: {len(scores)} companies, "
            f"{len(by_sector)} sectors, {elapsed:.0f}ms"
        )
        return scores

    async def apply_sector_constraints(
        self,
        scores: List[PnlEfficiencyScore],
        n_holdings: int = 20,
    ) -> List[PnlEfficiencyScore]:
        """Select top-N with sector-weight caps (mirrors RDAlphaScorer)."""
        if not scores:
            return []

        selected: List[PnlEfficiencyScore] = []
        sector_counts: Dict[str, int] = {}

        for score in scores:
            current_weight = sector_counts.get(score.sector, 0) / n_holdings if n_holdings > 0 else 0
            if current_weight >= self.MAX_SECTOR_WEIGHT:
                continue
            selected.append(score)
            sector_counts[score.sector] = sector_counts.get(score.sector, 0) + 1
            if len(selected) >= n_holdings:
                break

        total = len(selected)
        for s in selected:
            s.weight = 1.0 / total if total > 0 else 0.0

        for i, s in enumerate(selected):
            s.selection_rank = i + 1

        return selected

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _fetch_financials(
        self, data_year: Optional[int], min_revenue: float
    ) -> List[dict]:
        """Pull latest FY income-statement rows joined with sector metadata."""
        conditions = [
            or_(
                FMPIncomeStatement.period == None,
                FMPIncomeStatement.period == "FY",
            ),
            FMPIncomeStatement.revenue.isnot(None),
            FMPIncomeStatement.revenue >= min_revenue,
        ]

        if data_year is not None:
            conditions.append(FMPIncomeStatement.fiscal_year == data_year)

        query = (
            select(
                FMPIncomeStatement.symbol,
                FMPIncomeStatement.fiscal_year,
                FMPIncomeStatement.revenue,
                FMPIncomeStatement.cost_of_revenue,
                FMPIncomeStatement.sga_expenses,
                FMPIncomeStatement.operating_expenses,
                FMPIncomeStatement.net_income,
                SP500Company.name,
                SP500Company.sector,
                SP500Company.sub_sector,
            )
            .join(SP500Company, SP500Company.symbol == FMPIncomeStatement.symbol)
            .where(*conditions)
        )

        if data_year is None:
            query = query.distinct(FMPIncomeStatement.symbol).order_by(
                FMPIncomeStatement.symbol,
                FMPIncomeStatement.fiscal_year.desc(),
                FMPIncomeStatement.date.desc(),
            )

        result = await self.session.execute(query)
        rows = result.fetchall()

        out: List[dict] = []
        for r in rows:
            symbol, fy, rev, cogs, sga, opex, ni, name, sector, industry = r
            if not rev or rev <= 0 or not sector:
                continue

            coverage = 0
            if cogs is not None:
                coverage |= 1
            if sga is not None:
                coverage |= 2
            if opex is not None:
                coverage |= 4
            if ni is not None:
                coverage |= 8

            out.append({
                "symbol": symbol,
                "fiscal_year": fy,
                "revenue": float(rev),
                "cogs": float(cogs) if cogs is not None else 0.0,
                "sga": float(sga) if sga is not None else 0.0,
                "opex": float(opex) if opex is not None else 0.0,
                "net_income": float(ni) if ni is not None else 0.0,
                "name": name or symbol,
                "sector": sector,
                "industry": industry,
                "coverage": coverage,
            })

        return out

    def _score_sector(
        self, companies: List[dict], sector: str
    ) -> List[PnlEfficiencyScore]:
        """Compute sector-relative z-scores and composite for one sector."""
        for c in companies:
            rev = c["revenue"]
            c["gross_eff"] = 1.0 - (c["cogs"] / rev)
            c["overhead_eff"] = 1.0 - (c["sga"] / rev)
            c["operating_eff"] = 1.0 - (c["opex"] / rev)
            c["profit_conv"] = c["net_income"] / rev

        components = ["gross_eff", "overhead_eff", "operating_eff", "profit_conv"]

        z_scores: Dict[str, List[float]] = {comp: [] for comp in components}
        for comp in components:
            vals = [c[comp] for c in companies]
            mu = mean(vals)
            sd = stdev(vals) if len(vals) > 1 else 1.0
            if sd < 1e-9:
                sd = 1.0
            for c in companies:
                z = (c[comp] - mu) / sd
                z = max(-WINSORIZE_LIMIT, min(WINSORIZE_LIMIT, z))
                z_scores[comp].append(z)

        scores: List[PnlEfficiencyScore] = []
        n = len(companies)

        sorted_composites = sorted(
            range(n),
            key=lambda i: mean(z_scores[comp][i] for comp in components),
            reverse=True,
        )
        rank_map = {idx: rank for rank, idx in enumerate(sorted_composites)}

        for i, c in enumerate(companies):
            composite = mean(z_scores[comp][i] for comp in components)
            pct = 1.0 - (rank_map[i] / max(n - 1, 1))

            scores.append(PnlEfficiencyScore(
                symbol=c["symbol"],
                name=c["name"],
                sector=sector,
                industry=c.get("industry"),
                gross_efficiency=c["gross_eff"],
                overhead_efficiency=c["overhead_eff"],
                operating_efficiency=c["operating_eff"],
                profit_conversion=c["profit_conv"],
                gross_efficiency_z=z_scores["gross_eff"][i],
                overhead_efficiency_z=z_scores["overhead_eff"][i],
                operating_efficiency_z=z_scores["operating_eff"][i],
                profit_conversion_z=z_scores["profit_conv"][i],
                composite_z=composite,
                sector_percentile=round(pct * 100, 1),
                final_score=composite,
                revenue=c["revenue"],
                fiscal_year_used=c["fiscal_year"],
                coverage_flags=c["coverage"],
            ))

        return scores
