"""
PATH: backend/app/services/rolling_window/_query.py
PURPOSE: Retrieve and aggregate pre-computed rolling window results
WHY: Read-only query methods that API endpoints use to serve stored results
FLOW:
  ┌────────────────────────┐   ┌──────────────────┐   ┌───────────────────┐
  │ get_stored_window_     │ → │ aggregate_windows │ → │ JSON response     │
  │ results (from DB)      │   │ (cross-window avg)│   │ to API layer      │
  └────────────────────────┘   └──────────────────┘   └───────────────────┘
"""

from typing import Dict, List

import numpy as np
from sqlalchemy import select

from app.db.models import RollingWindowResult
from app.core.logging import get_logger

logger = get_logger(__name__)


class QueryMixin:
    """Mixin: query and aggregate stored rolling-window results."""

    async def get_stored_window_results(
        self,
        window_type: str
    ) -> List[Dict]:
        """Get pre-computed window results from database."""
        return_convention = "july_june" if self.use_july_june else "calendar"

        result = await self.session.execute(
            select(RollingWindowResult)
            .where(
                RollingWindowResult.window_type == window_type,
                RollingWindowResult.return_convention == return_convention,
                RollingWindowResult.data_tier == self.data_tier,
            )
            .order_by(RollingWindowResult.start_year, RollingWindowResult.quintile)
        )
        rows = result.scalars().all()

        # Group by window
        windows = {}
        for r in rows:
            key = (r.start_year, r.end_year)
            if key not in windows:
                windows[key] = {
                    "window_type": r.window_type,
                    "start_year": r.start_year,
                    "end_year": r.end_year,
                    "quintiles": []
                }
            windows[key]["quintiles"].append({
                "quintile": r.quintile,
                "n_companies": r.n_companies,
                "avg_rd_intensity": r.avg_rd_intensity,
                "median_rd_intensity": r.median_rd_intensity,
                "avg_return": r.avg_return,
                "median_return": r.median_return,
                "total_return": r.total_return,
                "annualized_return": r.annualized_return,
                "volatility": r.volatility,
                "sharpe_ratio": r.sharpe_ratio,
                "max_drawdown": r.max_drawdown,
            })

        # Calculate premium for each window
        results = []
        for key, window in sorted(windows.items()):
            quintiles = window["quintiles"]
            q1 = next((q for q in quintiles if q["quintile"] == 1), None)
            q5 = next((q for q in quintiles if q["quintile"] == 5), None)
            window["rd_premium"] = round((q5["avg_return"] or 0) - (q1["avg_return"] or 0), 2) if q1 and q5 else 0
            results.append(window)

        return results

    async def aggregate_windows(self, window_type: str) -> List[Dict]:
        """
        Aggregate pre-computed rolling-window results across all windows for a given horizon.

        This is a convenience method used by multiple API endpoints (e.g., export tables and
        net-of-cost analysis). It **does not recompute** windows; it summarizes stored results
        from `RollingWindowResult`.

        Returns:
            List[Dict] with one row per quintile containing average metrics across windows.
        """
        windows = await self.get_stored_window_results(window_type)
        if not windows:
            return []

        # Collect per-quintile metrics across windows
        per_q: Dict[int, Dict[str, List[float]]] = {
            q: {
                "n_companies": [],
                "avg_rd_intensity": [],
                "median_rd_intensity": [],
                "avg_return": [],
                "median_return": [],
                "total_return": [],
                "annualized_return": [],
                "volatility": [],
                "sharpe_ratio": [],
                "max_drawdown": [],
            }
            for q in range(1, 6)
        }

        for w in windows:
            for q in w.get("quintiles", []):
                qn = int(q.get("quintile", 0) or 0)
                if qn not in per_q:
                    continue

                # Note: stored values are already in *percent units* for returns/volatility/intensity.
                per_q[qn]["n_companies"].append(float(q.get("n_companies") or 0))
                if q.get("avg_rd_intensity") is not None:
                    per_q[qn]["avg_rd_intensity"].append(float(q["avg_rd_intensity"]))
                if q.get("median_rd_intensity") is not None:
                    per_q[qn]["median_rd_intensity"].append(float(q["median_rd_intensity"]))
                if q.get("avg_return") is not None:
                    per_q[qn]["avg_return"].append(float(q["avg_return"]))
                if q.get("median_return") is not None:
                    per_q[qn]["median_return"].append(float(q["median_return"]))
                if q.get("total_return") is not None:
                    per_q[qn]["total_return"].append(float(q["total_return"]))
                if q.get("annualized_return") is not None:
                    per_q[qn]["annualized_return"].append(float(q["annualized_return"]))
                if q.get("volatility") is not None:
                    per_q[qn]["volatility"].append(float(q["volatility"]))
                if q.get("sharpe_ratio") is not None:
                    per_q[qn]["sharpe_ratio"].append(float(q["sharpe_ratio"]))
                if q.get("max_drawdown") is not None:
                    per_q[qn]["max_drawdown"].append(float(q["max_drawdown"]))

        def mean_or_none(vals: List[float]) -> float | None:
            return float(np.mean(vals)) if vals else None

        n_windows = len(windows)
        aggregated: List[Dict] = []
        for qn in range(1, 6):
            aggregated.append({
                "quintile": qn,
                "label": f"Q{qn}",
                "n_windows": n_windows,
                "n_companies": int(round(mean_or_none(per_q[qn]["n_companies"]) or 0)),
                "avg_rd_intensity": mean_or_none(per_q[qn]["avg_rd_intensity"]),
                "median_rd_intensity": mean_or_none(per_q[qn]["median_rd_intensity"]),
                "avg_return": mean_or_none(per_q[qn]["avg_return"]),
                "median_return": mean_or_none(per_q[qn]["median_return"]),
                "total_return": mean_or_none(per_q[qn]["total_return"]),
                "annualized_return": mean_or_none(per_q[qn]["annualized_return"]),
                "volatility": mean_or_none(per_q[qn]["volatility"]),
                "sharpe_ratio": mean_or_none(per_q[qn]["sharpe_ratio"]),
                "max_drawdown": mean_or_none(per_q[qn]["max_drawdown"]),
            })

        return aggregated

    def calculate_weighted_return(
        self,
        companies: List[Dict],
        weighting: str = "equal"
    ) -> float:
        """
        Calculate portfolio return with specified weighting scheme.

        Args:
            companies: List of dicts with 'return' and optionally 'market_cap' keys
            weighting: 'equal' or 'value' (market cap weighted)

        Returns:
            Weighted portfolio return
        """
        if not companies:
            return 0.0

        returns = [c.get("return", 0) or 0 for c in companies]

        if weighting == "value":
            market_caps = [c.get("market_cap", 1) or 1 for c in companies]
            total_cap = sum(market_caps)
            if total_cap > 0:
                weights = [cap / total_cap for cap in market_caps]
                return float(np.average(returns, weights=weights))

        # Default: equal weight
        return float(np.mean(returns))
