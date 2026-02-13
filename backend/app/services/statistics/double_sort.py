# EXEMPTION: 315 lines — Single double-sort analysis method with complex nested portfolio construction
"""
PATH: backend/app/services/statistics/double_sort.py
PURPOSE: Double-sort analysis (Size x R&D Intensity).
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional, Any
import numpy as np
from sqlalchemy import select, func, text

from app.core.logging import get_logger

logger = get_logger(__name__)


class DoubleSortMixin:
    """Mixin providing double-sort portfolio analysis."""

    async def run_double_sort_analysis(
        self,
        start_year: int = 1995,
        end_year: int = 2024,
        use_july_june: bool = True
    ) -> Dict[str, Any]:
        """
        Run double-sort analysis: Size × R&D Intensity.
        
        Purpose: Show that R&D premium exists within BOTH small-cap and large-cap firms.
        This rules out the hypothesis that R&D is just a proxy for size.
        
        Method:
        1. Sort companies into Size terciles (Small, Medium, Large)
        2. Within each Size tercile, sort into R&D terciles (Low, Medium, High)
        3. Compute average returns for each of the 9 portfolios
        4. Test if High-Low R&D spread is significant within each size group
        
        PUBLICATION FIX (Dec 2025):
        - Now uses July-June returns by default (Fama-French convention)
        - Enforces point-in-time S&P 500 membership at formation date when membership spans are available
        
        Returns:
            9-cell matrix of returns with significance tests
        """
        from sqlalchemy import text
        import pandas as pd
        from app.db.models import SP500HistoricalConstituent
        from datetime import date

        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        all_year_data = []
        
        for year in range(start_year, end_year):
            formation_year = year
            return_year = year + 1
            formation_date = date(int(return_year), 7, 1) if use_july_june else date(int(return_year), 1, 1)
            
            if use_july_june:
                if membership_available:
                    q = text("""
                        WITH members AS (
                            SELECT DISTINCT symbol
                            FROM sp500_historical_constituents
                            WHERE added_date <= :formation_date
                              AND (removed_date IS NULL OR removed_date >= :formation_date)
                        ),
                        company_data AS (
                            SELECT 
                                inc.symbol,
                                inc.revenue,
                                CASE 
                                    WHEN inc.revenue > 100000000 
                                    THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL 
                                END as rd_intensity,
                                LOG(NULLIF(inc.revenue, 0)) as log_size
                            FROM fmp_income_statements inc
                            JOIN members m ON m.symbol = inc.symbol
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.revenue >= 100000000
                              AND inc.rd_expenses >= 0
                        ),
                        returns AS (
                            SELECT symbol, annualized_return * 100 as return_pct
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        )
                        SELECT 
                            cd.symbol,
                            cd.rd_intensity,
                            cd.log_size,
                            cd.revenue,
                            r.return_pct
                        FROM company_data cd
                        LEFT JOIN returns r ON cd.symbol = r.symbol
                        WHERE cd.rd_intensity IS NOT NULL
                          AND cd.log_size IS NOT NULL
                    """)
                else:
                    q = text("""
                        WITH company_data AS (
                            SELECT 
                                inc.symbol,
                                inc.revenue,
                                CASE 
                                    WHEN inc.revenue > 100000000 
                                    THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL 
                                END as rd_intensity,
                                LOG(NULLIF(inc.revenue, 0)) as log_size
                            FROM fmp_income_statements inc
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.revenue >= 100000000
                              AND inc.rd_expenses >= 0
                        ),
                        returns AS (
                            SELECT symbol, annualized_return * 100 as return_pct
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        )
                        SELECT 
                            cd.symbol,
                            cd.rd_intensity,
                            cd.log_size,
                            cd.revenue,
                            r.return_pct
                        FROM company_data cd
                        LEFT JOIN returns r ON cd.symbol = r.symbol
                        WHERE cd.rd_intensity IS NOT NULL
                          AND cd.log_size IS NOT NULL
                    """)
            else:
                q = text("""
                    WITH company_data AS (
                        SELECT 
                            inc.symbol,
                            inc.revenue,
                            CASE 
                                WHEN inc.revenue > 100000000 
                                THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity,
                            LOG(NULLIF(inc.revenue, 0)) as log_size
                        FROM fmp_income_statements inc
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.revenue >= 100000000
                          AND inc.rd_expenses >= 0
                    ),
                    returns AS (
                        SELECT symbol, annual_return * 100 as return_pct
                        FROM fmp_annual_returns
                        WHERE year = :return_year
                    )
                    SELECT 
                        cd.symbol,
                        cd.rd_intensity,
                        cd.log_size,
                        cd.revenue,
                        r.return_pct
                    FROM company_data cd
                    LEFT JOIN returns r ON cd.symbol = r.symbol
                    WHERE cd.rd_intensity IS NOT NULL
                      AND cd.log_size IS NOT NULL
                """)
            
            params = {"formation_year": formation_year, "return_year": return_year, "data_tier": self.data_tier}
            if use_july_june and membership_available:
                params["formation_date"] = formation_date

            result = await self.session.execute(q, params)
            rows = result.fetchall()
            
            if len(rows) < 50:
                continue
            
            df_rows = []
            
            for r in rows:
                symbol = r[0]
                return_pct = r[4]
                
                if return_pct is None:
                    continue  # Skip if no return
                return_pct = float(return_pct)
                
                df_rows.append({
                    "year": year,
                    "symbol": symbol,
                    "rd_intensity": float(r[1]),
                    "log_size": float(r[2]),
                    "revenue": float(r[3]),
                    "return_pct": return_pct
                })
            
            if len(df_rows) < 50:
                continue
            
            df = pd.DataFrame(df_rows)
            
            # Assign Size tercile
            df["size_tercile"] = pd.qcut(df["log_size"], 3, labels=["Small", "Medium", "Large"])
            
            # Within each size group, assign R&D tercile
            def assign_rd_tercile(group):
                try:
                    group["rd_tercile"] = pd.qcut(
                        group["rd_intensity"], 3, labels=["Low", "Medium", "High"]
                    )
                except ValueError:
                    # Not enough unique values
                    group["rd_tercile"] = pd.cut(
                        group["rd_intensity"].rank(method='first'), 
                        3, labels=["Low", "Medium", "High"]
                    )
                return group
            
            df = df.groupby("size_tercile", group_keys=False).apply(assign_rd_tercile)
            all_year_data.append(df)
        
        if not all_year_data:
            return {"error": "Insufficient data for double-sort analysis"}
        
        combined = pd.concat(all_year_data, ignore_index=True)
        
        # Compute average returns for each Size × R&D cell
        matrix = combined.groupby(["size_tercile", "rd_tercile"])["return_pct"].agg(
            ["mean", "std", "count"]
        ).round(2)
        
        # Convert to dictionary format
        results = {
            "methodology": "Double-Sort: Size × R&D Intensity",
            "n_years": len(all_year_data),
            "total_observations": len(combined),
            "matrix": {}
        }
        
        for size in ["Small", "Medium", "Large"]:
            results["matrix"][size] = {}
            for rd in ["Low", "Medium", "High"]:
                try:
                    cell = matrix.loc[(size, rd)]
                    results["matrix"][size][rd] = {
                        "mean_return": float(cell["mean"]),
                        "std": float(cell["std"]),
                        "n_obs": int(cell["count"])
                    }
                except KeyError:
                    results["matrix"][size][rd] = {"mean_return": None, "std": None, "n_obs": 0}
        
        # Compute High-Low R&D spread within each size group
        spreads = {}
        for size in ["Small", "Medium", "Large"]:
            high_ret = results["matrix"][size]["High"]["mean_return"]
            low_ret = results["matrix"][size]["Low"]["mean_return"]
            
            if high_ret is not None and low_ret is not None:
                spread = high_ret - low_ret
                
                # Get underlying returns for t-test
                high_returns = combined[
                    (combined["size_tercile"] == size) & (combined["rd_tercile"] == "High")
                ]["return_pct"].tolist()
                low_returns = combined[
                    (combined["size_tercile"] == size) & (combined["rd_tercile"] == "Low")
                ]["return_pct"].tolist()
                
                ttest = self.run_ttest(low_returns, high_returns)
                
                spreads[size] = {
                    "high_minus_low": round(spread, 2),
                    "t_stat": round(ttest.t_statistic, 2),
                    "p_value": round(ttest.p_value, 4),
                    "significant": bool(ttest.significant)
                }
        
        results["rd_spreads_by_size"] = spreads
        
        # Key finding: Is R&D premium significant in both Small and Large caps?
        small_sig = spreads.get("Small", {}).get("significant", False)
        large_sig = spreads.get("Large", {}).get("significant", False)
        
        results["key_findings"] = {
            "rd_works_in_small_caps": small_sig,
            "rd_works_in_large_caps": large_sig,
            "rd_is_not_just_size_effect": small_sig or large_sig
        }
        
        results["interpretation"] = (
            f"The R&D premium is {'significant' if small_sig else 'not significant'} among small-cap "
            f"firms (spread = {spreads.get('Small', {}).get('high_minus_low', 'N/A')}%, "
            f"t = {spreads.get('Small', {}).get('t_stat', 'N/A')}), "
            f"and {'significant' if large_sig else 'not significant'} among large-cap firms "
            f"(spread = {spreads.get('Large', {}).get('high_minus_low', 'N/A')}%, "
            f"t = {spreads.get('Large', {}).get('t_stat', 'N/A')}). "
            f"This {'confirms' if (small_sig or large_sig) else 'does not confirm'} that "
            f"R&D intensity captures return-relevant information beyond what is explained by firm size."
        )
        
        results["methodology_notes"] = {
            "return_type": "July-June (Fama-French convention)" if use_july_june else "Calendar year",
            "survivorship_correction": "Delisting returns integrated",
            "formation_rule": "FY(T) characteristics -> Returns July(T+1) to June(T+2)" if use_july_june else "FY(T) characteristics -> Calendar year T+1 returns"
        }
        
        return results
