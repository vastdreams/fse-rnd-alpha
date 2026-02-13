# EXEMPTION: 301 lines — Core calculation mixin at the 300-line boundary; single-line trimming would lose clarity
"""
PATH: backend/app/services/rolling_window/_calculator.py
PURPOSE: Quintile statistics calculation and rolling window computation
WHY: Core computation logic for quintile stats, single-window returns,
     and all-windows batch computation with DB persistence
FLOW:
  ┌──────────────────┐   ┌────────────────────┐   ┌─────────────────────────┐
  │ calculate_stats  │ → │ compute_quintile   │ → │ compute_all_rolling     │
  │ (per quintile)   │   │ _returns (1 window)│   │ _windows (all windows)  │
  └──────────────────┘   └────────────────────┘   └─────────────────────────┘
"""

from typing import Dict, List, Tuple

import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FMPIncomeStatement, RollingWindowResult
from app.core.logging import get_logger
from ._models import QuintileResult

logger = get_logger(__name__)


class CalculatorMixin:
    """Mixin: quintile statistics and rolling window computation."""

    async def calculate_quintile_stats(
        self,
        quintile: int,
        companies: List[Dict],
        window_length: int,
        window_years: List[int]
    ) -> QuintileResult:
        """
        Calculate statistics for a quintile using PROPER TIME-SERIES methodology.

        Survivorship Correction:
        - Delistings are handled upstream in the July–June return series (return ends at last observed price;
          cash is treated as earning 0% thereafter for the remainder of the window).
        - Uses time-varying risk-free rate from database.
        """
        if not companies:
            return QuintileResult(
                quintile=quintile,
                n_companies=0,
                symbols=[],
                avg_rd_intensity=0,
                median_rd_intensity=0,
                avg_return=0,
                median_return=0,
                total_return=0,
                annualized_return=0,
                volatility=0,
                sharpe_ratio=0
            )

        symbols = [c["symbol"] for c in companies]
        rd_intensities = [c["rd_intensity"] for c in companies]

        def safe_float(val):
            """Convert NaN/Inf to 0."""
            if val is None or np.isnan(val) or np.isinf(val):
                return 0.0
            return float(val)

        # Calculate equal-weighted portfolio return for each year in window
        portfolio_returns = []

        for year in window_years:
            year_returns = []
            rf_rate = await self.get_risk_free_rate(year)

            for c in companies:
                symbol = c["symbol"]

                # Normal return
                if "returns" in c and year in c["returns"]:
                    ret = c["returns"][year]
                    if ret is not None and not np.isnan(ret):
                        year_returns.append(ret)

            if year_returns:
                portfolio_returns.append(np.mean(year_returns))
            else:
                # Fallback to RF if no companies left (unlikely)
                portfolio_returns.append(rf_rate)

        if not portfolio_returns:
            return QuintileResult(
                quintile=quintile, n_companies=len(companies), symbols=symbols,
                avg_rd_intensity=safe_float(np.mean(rd_intensities)),
                median_rd_intensity=safe_float(np.median(rd_intensities)),
                avg_return=0, median_return=0, total_return=0, annualized_return=0,
                volatility=0, sharpe_ratio=0, max_drawdown=0
            )

        # Time-series statistics
        mean_return = float(np.mean(portfolio_returns))

        compound_product = 1.0
        for r in portfolio_returns:
            compound_product *= (1 + r)
        total_return = compound_product - 1

        n_periods = len(portfolio_returns)
        annualized_return = (compound_product ** (1 / n_periods) - 1) if n_periods > 0 else 0

        volatility = float(np.std(portfolio_returns, ddof=1)) if len(portfolio_returns) > 1 else 0

        # Sharpe ratio with time-varying RF
        avg_rf = np.mean([await self.get_risk_free_rate(y) for y in window_years])
        excess_return = annualized_return - avg_rf
        sharpe = excess_return / volatility if volatility > 0 else 0

        # Max drawdown calculation
        cumulative = np.cumprod([1 + r for r in portfolio_returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = cumulative / running_max - 1
        max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else 0.0

        return QuintileResult(
            quintile=quintile,
            n_companies=len(companies),
            symbols=symbols,
            avg_rd_intensity=safe_float(np.mean(rd_intensities)),
            median_rd_intensity=safe_float(np.median(rd_intensities)),
            avg_return=mean_return * 100,
            median_return=safe_float(np.median(portfolio_returns)) * 100,
            total_return=total_return * 100,
            annualized_return=annualized_return * 100,
            volatility=volatility * 100,
            sharpe_ratio=sharpe,
            max_drawdown=max_drawdown * 100  # Store as percent
        )

    async def compute_quintile_returns(
        self,
        window_type: str,
        start_year: int,
        end_year: int
    ) -> List[QuintileResult]:
        """
        Compute quintile returns for a specific window.
        """
        window_length = self.WINDOW_LENGTHS.get(window_type, 5)
        window_years = list(range(start_year, end_year + 1))

        # Get eligible companies
        companies = await self.get_eligible_companies(window_type, start_year, end_year)

        if len(companies) < 10:
            logger.warning(f"Insufficient companies for {window_type} window {start_year}-{end_year}: {len(companies)}")
            return []

        # Assign to quintiles
        quintiles = self.assign_quintiles(companies)

        # Calculate stats for each quintile (ASYNCHRONOUSLY)
        results = []
        for q in range(1, 6):
            stats = await self.calculate_quintile_stats(q, quintiles[q], window_length, window_years)
            results.append(stats)

        return results

    async def compute_all_rolling_windows(
        self,
        window_type: str,
        save_results: bool = True
    ) -> List[Dict]:
        """
        Generate all possible rolling windows for a given type.

        - 5yr: 1995-2000, 1996-2001, ... 2020-2025
        - 10yr: 1995-2005, 1996-2006, ... 2015-2025
        - 20yr: 1995-2015, 1996-2016, ... 2005-2025
        """
        window_length = self.WINDOW_LENGTHS.get(window_type, 5)

        # Determine available year range from data
        year_result = await self.session.execute(
            select(
                func.min(FMPIncomeStatement.fiscal_year),
                func.max(FMPIncomeStatement.fiscal_year)
            )
        )
        min_year, max_year = year_result.fetchone()

        if not min_year or not max_year:
            return []

        # Generate all windows
        all_results = []

        # Versioning metadata for stored results (Dec 2025)
        return_convention = "july_june" if self.use_july_june else "calendar"

        # Preload existing rows so recomputation is idempotent and does not duplicate rows.
        existing_by_key: Dict[Tuple[int, int, int], RollingWindowResult] = {}
        if save_results:
            existing_result = await self.session.execute(
                select(RollingWindowResult)
                .where(
                    RollingWindowResult.window_type == window_type,
                    RollingWindowResult.return_convention == return_convention,
                    RollingWindowResult.data_tier == self.data_tier,
                )
            )
            for row in existing_result.scalars().all():
                existing_by_key[(row.start_year, row.end_year, row.quintile)] = row

        for start_year in range(min_year, max_year - window_length + 2):
            end_year = start_year + window_length - 1

            if end_year > max_year:
                break

            logger.info(f"Computing {window_type} window: {start_year}-{end_year}")

            quintile_results = await self.compute_quintile_returns(
                window_type, start_year, end_year
            )

            if not quintile_results:
                continue

            window_result = {
                "window_type": window_type,
                "start_year": start_year,
                "end_year": end_year,
                "quintiles": [
                    {
                        "quintile": r.quintile,
                        "n_companies": r.n_companies,
                        "avg_rd_intensity": round(r.avg_rd_intensity, 2),
                        "avg_return": round(r.avg_return, 2),
                        "total_return": round(r.total_return, 2),
                        "volatility": round(r.volatility, 2),
                        "sharpe_ratio": round(r.sharpe_ratio, 3)
                    }
                    for r in quintile_results
                ],
                "rd_premium": round(quintile_results[4].avg_return - quintile_results[0].avg_return, 2)
                    if len(quintile_results) == 5 else 0
            }

            all_results.append(window_result)

            # Save to database
            if save_results:
                for r in quintile_results:
                    natural_key = (start_year, end_year, r.quintile)
                    existing = existing_by_key.get(natural_key)

                    if existing:
                        # Update existing row (idempotent recomputation)
                        existing.return_convention = return_convention
                        existing.data_tier = self.data_tier
                        existing.computation_run_id = self.computation_run_id

                        existing.n_companies = r.n_companies
                        existing.avg_rd_intensity = r.avg_rd_intensity
                        existing.median_rd_intensity = r.median_rd_intensity
                        existing.avg_return = r.avg_return
                        existing.median_return = r.median_return
                        existing.total_return = r.total_return
                        existing.annualized_return = r.annualized_return
                        existing.volatility = r.volatility
                        existing.sharpe_ratio = r.sharpe_ratio
                        existing.max_drawdown = r.max_drawdown
                    else:
                        db_result = RollingWindowResult(
                            window_type=window_type,
                            start_year=start_year,
                            end_year=end_year,
                            quintile=r.quintile,
                            # Versioning metadata (Dec 2025)
                            return_convention=return_convention,
                            data_tier=self.data_tier,
                            computation_run_id=self.computation_run_id,
                            # Portfolio statistics
                            n_companies=r.n_companies,
                            avg_rd_intensity=r.avg_rd_intensity,
                            median_rd_intensity=r.median_rd_intensity,
                            avg_return=r.avg_return,
                            median_return=r.median_return,
                            total_return=r.total_return,
                            annualized_return=r.annualized_return,
                            volatility=r.volatility,
                            sharpe_ratio=r.sharpe_ratio,
                            max_drawdown=r.max_drawdown,
                        )
                        self.session.add(db_result)
                        existing_by_key[natural_key] = db_result

        if save_results:
            await self.session.commit()

        return all_results
