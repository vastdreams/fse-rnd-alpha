# EXEMPTION: 334 lines — Five ANOVA methods sharing internal state; splitting would fragment the analysis pipeline
"""
PATH: backend/app/services/statistics/anova.py
PURPOSE: ANOVA-related statistical methods (one-way ANOVA, Tukey HSD, quintile ANOVA, aggregate).
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional
import numpy as np
from scipy import stats
from sqlalchemy import select

from app.db.models import RollingWindowResult, AnovaResult
from app.core.logging import get_logger
from app.services.statistics.models import AnovaTestResult

logger = get_logger(__name__)


class AnovaMixin:
    """Mixin providing ANOVA-related statistical methods."""

    def run_anova(
        self,
        groups: Dict[int, List[float]]
    ) -> AnovaTestResult:
        """
        Run one-way ANOVA comparing returns across quintiles.
        
        Args:
            groups: Dict mapping quintile (1-5) to list of returns
            
        Returns:
            AnovaTestResult with F-statistic, p-value, effect sizes
        """
        # Filter out empty groups
        valid_groups = {k: v for k, v in groups.items() if v}
        
        if len(valid_groups) < 2:
            return AnovaTestResult(
                f_statistic=0,
                p_value=1,
                eta_squared=0,
                omega_squared=0,
                significant_005=False,
                significant_001=False,
                group_means={},
                group_stds={},
                group_ns={},
                tukey_results=None
            )
        
        # Prepare data for ANOVA
        group_list = [np.array(v) for v in valid_groups.values()]
        
        # Run one-way ANOVA
        f_stat, p_value = stats.f_oneway(*group_list)
        
        # Calculate effect sizes
        # Eta-squared: SS_between / SS_total
        all_data = np.concatenate(group_list)
        grand_mean = np.mean(all_data)
        
        ss_between = sum(
            len(g) * (np.mean(g) - grand_mean) ** 2 
            for g in group_list
        )
        ss_total = np.sum((all_data - grand_mean) ** 2)
        
        eta_squared = ss_between / ss_total if ss_total > 0 else 0
        
        # Omega-squared (less biased)
        n_total = len(all_data)
        k = len(group_list)
        ms_within = (ss_total - ss_between) / (n_total - k)
        omega_squared = (ss_between - (k - 1) * ms_within) / (ss_total + ms_within)
        omega_squared = max(0, omega_squared)
        
        # Group statistics - convert NaN to None for JSON compatibility
        def safe_float(val):
            if np.isnan(val) or np.isinf(val):
                return None
            return float(val)
        
        group_means = {k: safe_float(np.mean(v)) for k, v in valid_groups.items()}
        group_stds = {k: safe_float(np.std(v, ddof=1)) if len(v) > 1 else 0 for k, v in valid_groups.items()}
        group_ns = {k: len(v) for k, v in valid_groups.items()}
        
        # Tukey HSD post-hoc (pairwise comparisons)
        tukey_results = self._tukey_hsd(valid_groups)
        
        return AnovaTestResult(
            f_statistic=safe_float(f_stat) or 0,
            p_value=safe_float(p_value) or 1,
            eta_squared=safe_float(eta_squared) or 0,
            omega_squared=safe_float(omega_squared) or 0,
            significant_005=bool(p_value < 0.05) if not np.isnan(p_value) else False,
            significant_001=bool(p_value < 0.01) if not np.isnan(p_value) else False,
            group_means=group_means,
            group_stds=group_stds,
            group_ns=group_ns,
            tukey_results=tukey_results
        )
    
    def _tukey_hsd(self, groups: Dict[int, List[float]]) -> Dict:
        """Perform Tukey HSD post-hoc pairwise comparisons."""
        try:
            from scipy.stats import tukey_hsd
            
            keys = sorted(groups.keys())
            group_list = [np.array(groups[k]) for k in keys]
            
            result = tukey_hsd(*group_list)
            
            # Extract pairwise comparisons
            comparisons = {}
            for i, k1 in enumerate(keys):
                for j, k2 in enumerate(keys):
                    if i < j:
                        key = f"Q{k1}_vs_Q{k2}"
                        comparisons[key] = {
                            "statistic": float(result.statistic[i, j]),
                            "p_value": float(result.pvalue[i, j]),
                            "significant": bool(result.pvalue[i, j] < 0.05)
                        }
            
            return comparisons
        except Exception as e:
            logger.warning(f"Tukey HSD failed: {e}")
            return {}

    async def run_quintile_anova(
        self,
        window_type: str,
        period: str,
        save_results: bool = True
    ) -> AnovaTestResult:
        """
        Run ANOVA for quintile returns in a specific window.
        
        Args:
            window_type: "5yr", "10yr", or "20yr"
            period: Window period string, e.g., "2000-2005"
        """
        start_year, end_year = map(int, period.split("-"))
        
        # Get quintile returns from stored results
        result = await self.session.execute(
            select(RollingWindowResult)
            .where(RollingWindowResult.window_type == window_type)
            .where(RollingWindowResult.start_year == start_year)
            .where(RollingWindowResult.end_year == end_year)
        )
        rows = result.scalars().all()
        
        if not rows:
            return None
        
        # Build groups (using average returns as proxy)
        groups = {}
        for r in rows:
            if r.avg_return is not None:
                groups[r.quintile] = [r.avg_return]  # Single observation per quintile for this window
        
        anova_result = self.run_anova(groups)
        
        # Also run t-test for Q5 vs Q1
        q1_return = next((r.avg_return for r in rows if r.quintile == 1), None)
        q5_return = next((r.avg_return for r in rows if r.quintile == 5), None)
        
        if q1_return is not None and q5_return is not None:
            high_low_diff = q5_return - q1_return
            if np.isnan(high_low_diff) or np.isinf(high_low_diff):
                high_low_diff = None
        else:
            high_low_diff = None
        
        if save_results:
            return_convention = "july_june" if self.use_july_june else "calendar"

            existing = await self.session.scalar(
                select(AnovaResult)
                .where(
                    AnovaResult.window_type == window_type,
                    AnovaResult.period == period,
                    AnovaResult.test_type == "one_way_anova",
                    AnovaResult.return_convention == return_convention,
                    AnovaResult.data_tier == self.data_tier,
                )
                .limit(1)
            )

            if existing:
                existing.f_statistic = anova_result.f_statistic
                existing.p_value = anova_result.p_value
                existing.eta_squared = anova_result.eta_squared
                existing.omega_squared = anova_result.omega_squared
                existing.significant_005 = anova_result.significant_005
                existing.significant_001 = anova_result.significant_001
                existing.group_means = anova_result.group_means
                existing.group_stds = anova_result.group_stds
                existing.group_ns = anova_result.group_ns
                existing.tukey_results = anova_result.tukey_results
                existing.high_low_diff = high_low_diff
            else:
                db_result = AnovaResult(
                    window_type=window_type,
                    period=period,
                    test_type="one_way_anova",
                    return_convention=return_convention,
                    data_tier=self.data_tier,
                f_statistic=anova_result.f_statistic,
                p_value=anova_result.p_value,
                eta_squared=anova_result.eta_squared,
                omega_squared=anova_result.omega_squared,
                significant_005=anova_result.significant_005,
                significant_001=anova_result.significant_001,
                group_means=anova_result.group_means,
                    group_stds=anova_result.group_stds,
                    group_ns=anova_result.group_ns,
                    tukey_results=anova_result.tukey_results,
                    high_low_diff=high_low_diff,
                )
                self.session.add(db_result)

            await self.session.commit()
        
        return anova_result
    
    async def run_all_anovas(
        self,
        window_type: str
    ) -> List[Dict]:
        """Run ANOVA for all windows of a given type."""
        return_convention = "july_june" if self.use_july_june else "calendar"

        # Get all unique windows
        result = await self.session.execute(
            select(
                RollingWindowResult.start_year,
                RollingWindowResult.end_year
            )
            .where(
                RollingWindowResult.window_type == window_type,
                RollingWindowResult.return_convention == return_convention,
                RollingWindowResult.data_tier == self.data_tier,
            )
            .distinct()
            .order_by(RollingWindowResult.start_year)
        )
        windows = result.fetchall()
        
        all_results = []
        
        for start_year, end_year in windows:
            period = f"{start_year}-{end_year}"
            anova_result = await self.run_quintile_anova(
                window_type, period, save_results=True
            )
            
            if anova_result:
                all_results.append({
                    "period": period,
                    "f_statistic": round(anova_result.f_statistic, 3),
                    "p_value": round(anova_result.p_value, 4),
                    "eta_squared": round(anova_result.eta_squared, 3),
                    "significant": anova_result.significant_005,
                    "group_means": anova_result.group_means
                })
        
        logger.info(f"Completed ANOVA for {len(all_results)} {window_type} windows")
        
        return all_results
    
    async def compute_aggregate_anova(
        self,
        window_type: str
    ) -> Dict:
        """
        Compute aggregate ANOVA across all windows of a type.
        
        Pools returns across all windows for each quintile.
        """
        return_convention = "july_june" if self.use_july_june else "calendar"

        result = await self.session.execute(
            select(RollingWindowResult)
            .where(
                RollingWindowResult.window_type == window_type,
                RollingWindowResult.return_convention == return_convention,
                RollingWindowResult.data_tier == self.data_tier,
            )
        )
        rows = result.scalars().all()
        
        # Pool returns by quintile
        groups = {i: [] for i in range(1, 6)}
        
        for r in rows:
            if r.avg_return is not None:
                groups[r.quintile].append(r.avg_return)
        
        anova_result = self.run_anova(groups)
        
        # T-test for Q5 vs Q1
        ttest_result = self.run_ttest(groups[1], groups[5])
        
        return {
            "window_type": window_type,
            "n_windows": len(rows) // 5,
            "anova": {
                "f_statistic": float(round(anova_result.f_statistic, 3)),
                "p_value": float(round(anova_result.p_value, 6)),
                "eta_squared": float(round(anova_result.eta_squared, 3)),
                "omega_squared": float(round(anova_result.omega_squared, 3)),
                "significant_005": bool(anova_result.significant_005),
                "significant_001": bool(anova_result.significant_001)
            },
            "ttest_high_vs_low": {
                "t_statistic": float(round(ttest_result.t_statistic, 3)),
                "p_value": float(round(ttest_result.p_value, 6)),
                "mean_difference": float(round(ttest_result.mean_diff, 2)),
                "cohens_d": float(round(ttest_result.effect_size, 3)),
                "significant": bool(ttest_result.significant)
            },
            "quintile_means": {
                f"Q{k}": float(round(np.mean(v), 2)) if v else 0.0
                for k, v in groups.items()
            },
            "quintile_ns": {
                f"Q{k}": len(v) for k, v in groups.items()
            }
        }
