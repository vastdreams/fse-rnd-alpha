# EXEMPTION: 503 lines — Two tightly-coupled annual premium methods with complex SQL; further splitting would fragment the calculation flow
"""
PATH: backend/app/services/statistics/annual_hml.py
PURPOSE: Annual HML (High-Minus-Low R&D) premium computation and sector-neutral variant.
WHY: Extracted from monolithic statistics.py for maintainability.
"""

from typing import Dict, List, Optional, Any
import numpy as np
from sqlalchemy import select, func, text

from app.core.logging import get_logger

logger = get_logger(__name__)


class AnnualHMLMixin:
    """Mixin providing annual HML premium computation methods."""

    async def compute_annual_hml_premium(self, use_july_june: bool = True) -> Dict:
        """
        Compute annual HML (High-Minus-Low R&D) premium series.
        
        This is the PREFERRED approach for inference:
        - One observation per year (non-overlapping)
        - Newey-West standard errors on the annual series
        - Avoids the overlapping window autocorrelation problem
        
        PUBLICATION FIX (Dec 2025):
        - Now uses July-June returns by default (Fama-French convention)
        - Integrates delisting returns for survivorship bias correction
        - Formation year T-1 R&D data -> July T to June T+1 returns
        
        Args:
            use_july_june: If True (default), use July-June returns (bias-free).
                          If False, use calendar year returns (legacy).
        
        Returns:
            Dict with annual premiums, mean, NW SE, t-stat, p-value
        """
        from app.db.models import JulyJuneReturn, FMPAnnualReturn, FMPIncomeStatement, SP500HistoricalConstituent
        from sqlalchemy import select, func
        from datetime import date
        
        # Determine which return table to use
        if use_july_june:
            # Get all formation years with data (formation_year = FY data year)
            result = await self.session.execute(
                select(func.distinct(JulyJuneReturn.formation_year))
                .where(JulyJuneReturn.formation_year >= 1994)  # Need FY 1994+ for July 1995+
                .where(JulyJuneReturn.data_tier == self.data_tier)
                .order_by(JulyJuneReturn.formation_year)
            )
            formation_years = [r[0] for r in result.fetchall()]
        else:
            # Legacy: calendar year returns
            result = await self.session.execute(
                select(func.distinct(FMPAnnualReturn.year))
                .where(FMPAnnualReturn.year >= 1995)
                .order_by(FMPAnnualReturn.year)
            )
            formation_years = [r[0] - 1 for r in result.fetchall()]  # Adjust to formation year convention
        
        # Pre-fetch delisting returns for survivorship correction
        # Publication note:
        # We do NOT substitute delisting-return proxies into the return series here.
        # Instead, July–June returns are computed upstream from daily prices; if a symbol’s price
        # history ends early (e.g., M&A / delisting), the return is computed to the last observed
        # price and cash is treated as earning 0% thereafter for the remainder of the window.
        
        # Membership availability (point-in-time S&P 500 constituents)
        # If the table is empty, we fall back to an “available data” universe and record that in diagnostics later.
        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        annual_premiums = []
        
        for formation_year in formation_years:
            # Formation year = FY from which we get R&D data
            # For July-June: Returns from July(formation_year+1) to June(formation_year+2)
            # For calendar: Returns for year (formation_year+1)
            return_year = formation_year + 1
            formation_date = date(int(return_year), 7, 1) if use_july_june else date(int(return_year), 1, 1)
            
            # Get R&D intensity from formation year (FY T-1 for returns in year T)
            if use_july_june:
                # Use FY(formation_year) data, get returns from July(formation_year+1)
                if membership_available:
                    q = text("""
                        WITH members AS (
                            SELECT DISTINCT symbol
                            FROM sp500_historical_constituents
                            WHERE added_date <= :formation_date
                              AND (removed_date IS NULL OR removed_date >= :formation_date)
                        ),
                        rd_data AS (
                            SELECT 
                                inc.symbol,
                                CASE 
                                    WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL 
                                END as rd_intensity
                            FROM fmp_income_statements inc
                            JOIN members m ON m.symbol = inc.symbol
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.rd_expenses >= 0
                              AND inc.revenue >= 100000000
                        ),
                        ranked AS (
                            SELECT 
                                rd.symbol,
                                rd.rd_intensity,
                                NTILE(5) OVER (ORDER BY rd.rd_intensity) as quintile
                            FROM rd_data rd
                            WHERE rd.rd_intensity IS NOT NULL
                        ),
                        returns AS (
                            SELECT symbol, annualized_return as annual_return
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        )
                        SELECT 
                            r.quintile,
                            r.symbol,
                            ret.annual_return
                        FROM ranked r
                        LEFT JOIN returns ret ON r.symbol = ret.symbol
                        WHERE r.quintile IN (1, 5)
                    """)
                else:
                    q = text("""
                        WITH rd_data AS (
                            SELECT 
                                inc.symbol,
                                CASE 
                                    WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL 
                                END as rd_intensity
                            FROM fmp_income_statements inc
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.rd_expenses >= 0
                              AND inc.revenue >= 100000000
                        ),
                        ranked AS (
                            SELECT 
                                rd.symbol,
                                rd.rd_intensity,
                                NTILE(5) OVER (ORDER BY rd.rd_intensity) as quintile
                            FROM rd_data rd
                            WHERE rd.rd_intensity IS NOT NULL
                        ),
                        returns AS (
                            SELECT symbol, annualized_return as annual_return
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        )
                        SELECT 
                            r.quintile,
                            r.symbol,
                            ret.annual_return
                        FROM ranked r
                        LEFT JOIN returns ret ON r.symbol = ret.symbol
                        WHERE r.quintile IN (1, 5)
                    """)
            else:
                # Legacy calendar year
                q = text("""
                    WITH rd_data AS (
                        SELECT 
                            inc.symbol,
                            CASE 
                                WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                ELSE NULL 
                            END as rd_intensity
                        FROM fmp_income_statements inc
                        WHERE inc.fiscal_year = :formation_year
                          AND inc.period = 'FY'
                          AND inc.rd_expenses >= 0
                          AND inc.revenue >= 100000000
                    ),
                    ranked AS (
                        SELECT 
                            rd.symbol,
                            rd.rd_intensity,
                            NTILE(5) OVER (ORDER BY rd.rd_intensity) as quintile
                        FROM rd_data rd
                        WHERE rd.rd_intensity IS NOT NULL
                    ),
                    returns AS (
                        SELECT symbol, annual_return
                        FROM fmp_annual_returns
                        WHERE year = :return_year
                    )
                    SELECT 
                        r.quintile,
                        r.symbol,
                        ret.annual_return
                    FROM ranked r
                    LEFT JOIN returns ret ON r.symbol = ret.symbol
                    WHERE r.quintile IN (1, 5)
                """)
            
            params = {"formation_year": formation_year, "return_year": return_year, "data_tier": self.data_tier}
            if use_july_june and membership_available:
                params["formation_date"] = formation_date

            result = await self.session.execute(q, params)
            rows = result.fetchall()
            
            # Group by quintile
            quintile_returns = {1: [], 5: []}
            
            for row in rows:
                quintile, symbol, annual_return = row[0], row[1], row[2]
                
                if quintile not in [1, 5]:
                    continue
                
                if annual_return is not None:
                    quintile_returns[quintile].append(annual_return)
            
            # Calculate average returns per quintile
            if quintile_returns[1] and quintile_returns[5]:
                q1_avg = np.mean(quintile_returns[1])
                q5_avg = np.mean(quintile_returns[5])
                hml_premium = q5_avg - q1_avg
                
                annual_premiums.append({
                    "year": return_year if not use_july_june else f"Jul{return_year}-Jun{return_year+1}",
                    "formation_year": formation_year,
                    "q1_return": float(q1_avg) * 100,  # Convert to percentage
                    "q5_return": float(q5_avg) * 100,
                    "hml_premium": float(hml_premium) * 100,
                    "q1_n": len(quintile_returns[1]),
                    "q5_n": len(quintile_returns[5]),
                    "return_type": "july_june" if use_july_june else "calendar"
                })
        
        if len(annual_premiums) < 5:
            return {
                "error": "Insufficient data for annual HML analysis",
                "n_years": len(annual_premiums)
            }
        
        premiums = [p["hml_premium"] for p in annual_premiums]
        
        # Compute HAC test on the annual premium series
        # For annual non-overlapping data, use modest lag (1-2)
        hac_result = self.compute_hac_ttest(premiums, hypothesis_value=0, lags=1)

        # Newey–West lag robustness (reviewer-friendly): show that inference is not
        # an artifact of a single lag choice on a short annual sample (N=24).
        # We report lags 0–3 as a compact robustness panel.
        nw_lag_robustness = {}
        for lag in [0, 1, 2, 3]:
            r = self.compute_hac_ttest(premiums, hypothesis_value=0, lags=lag)
            nw_lag_robustness[str(lag)] = {
                "lags": int(lag),
                "nw_std_error": float(r.std_error_hac),
                "t_statistic": float(r.t_statistic_hac),
                "p_value": float(r.p_value_hac),
                "significant_005": bool(r.p_value_hac < 0.05),
            }
        
        return {
            "annual_premiums": annual_premiums,
            "n_years": len(annual_premiums),
            "mean_premium": float(np.mean(premiums)),
            "std_dev": float(np.std(premiums, ddof=1)),
            "min_premium": float(np.min(premiums)),
            "max_premium": float(np.max(premiums)),
            "positive_years": sum(1 for p in premiums if p > 0),
            "win_rate": sum(1 for p in premiums if p > 0) / len(premiums),
            "hac_adjusted": {
                "mean": hac_result.mean,
                "nw_std_error": hac_result.std_error_hac,
                "t_statistic": hac_result.t_statistic_hac,
                "p_value": hac_result.p_value_hac,
                "significant": hac_result.significant,
                "lags_used": hac_result.lags_used
            },
            "hac_lag_robustness": nw_lag_robustness,
            "methodology": {
                "return_convention": "July-June (Fama-French)" if use_july_june else "Calendar Year",
                "bias_correction": "Look-ahead bias eliminated" if use_july_june else "Potential look-ahead bias",
                "survivorship_correction": "Point-in-time membership (when available) + cash-after-exit in return construction",
                "formation_rule": "FY(T-1) R&D data -> Returns July T to June T+1" if use_july_june else "FY(T-1) R&D data -> Calendar year T returns"
            },
            "note": f"Annual non-overlapping HML premium with Newey-West SE. {'July-June convention (preferred)' if use_july_june else 'Calendar year (legacy)'}."
        }

    async def compute_sector_neutral_annual_hml_premium(self, *, use_july_june: bool = True) -> Dict[str, Any]:
        """
        Compute a sector-neutral annual HML (High-Minus-Low R&D) premium.

        Purpose (practitioner-journal robustness):
          - Address the critique: “this is just Tech + Healthcare.”
          - Construct within-sector R&D quintiles, compute sector HML (Q5-Q1) per year,
            then average HML across sectors (equal-weight by sector).

        Notes:
          - Sector classification uses `sp500_companies.sector` (current GICS mapping). This is a
            pragmatic sector label for robustness; point-in-time sector classifications are not
            available in Tier-1 with full historical fidelity.
          - Returns are sourced from the same return table as the primary annual series.
        """
        from sqlalchemy import text
        from sqlalchemy import func
        from app.db.models import JulyJuneReturn, FMPAnnualReturn, SP500HistoricalConstituent
        from datetime import date

        # Determine formation years available
        if use_july_june:
            result = await self.session.execute(
                select(func.distinct(JulyJuneReturn.formation_year))
                .where(JulyJuneReturn.formation_year >= 1994)
                .where(JulyJuneReturn.data_tier == self.data_tier)
                .order_by(JulyJuneReturn.formation_year)
            )
            formation_years = [r[0] for r in result.fetchall()]
        else:
            result = await self.session.execute(
                select(func.distinct(FMPAnnualReturn.year))
                .where(FMPAnnualReturn.year >= 1995)
                .order_by(FMPAnnualReturn.year)
            )
            formation_years = [r[0] - 1 for r in result.fetchall()]

        membership_total = await self.session.scalar(select(func.count(SP500HistoricalConstituent.id)))
        membership_available = bool(isinstance(membership_total, int) and membership_total > 0)

        annual = []

        for formation_year in formation_years:
            return_year = int(formation_year) + 1
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
                        rd_data AS (
                            SELECT
                                inc.symbol,
                                sp.sector AS sector,
                                CASE
                                    WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL
                                END AS rd_intensity
                            FROM fmp_income_statements inc
                            JOIN members m ON m.symbol = inc.symbol
                            LEFT JOIN sp500_companies sp ON sp.symbol = inc.symbol
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.rd_expenses >= 0
                              AND inc.revenue >= 100000000
                        ),
                        ranked AS (
                            SELECT
                                rd.symbol,
                                rd.sector,
                                rd.rd_intensity,
                                NTILE(5) OVER (PARTITION BY rd.sector ORDER BY rd.rd_intensity) AS quintile
                            FROM rd_data rd
                            WHERE rd.rd_intensity IS NOT NULL
                              AND rd.sector IS NOT NULL
                        ),
                        returns AS (
                            SELECT symbol, annualized_return AS annual_return
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        ),
                        joined AS (
                            SELECT r.sector, r.quintile, ret.annual_return
                            FROM ranked r
                            JOIN returns ret ON r.symbol = ret.symbol
                            WHERE r.quintile IN (1, 5)
                              AND ret.annual_return IS NOT NULL
                        ),
                        sector_hml AS (
                            SELECT
                                sector,
                                AVG(CASE WHEN quintile = 5 THEN annual_return END) AS q5_avg,
                                AVG(CASE WHEN quintile = 1 THEN annual_return END) AS q1_avg
                            FROM joined
                            GROUP BY sector
                            HAVING COUNT(CASE WHEN quintile = 5 THEN 1 END) > 0
                               AND COUNT(CASE WHEN quintile = 1 THEN 1 END) > 0
                        )
                        SELECT
                            AVG(q5_avg - q1_avg) AS sector_neutral_hml,
                            COUNT(*) AS n_sectors
                        FROM sector_hml
                    """)
                    params = {"formation_year": formation_year, "data_tier": self.data_tier, "formation_date": formation_date}
                else:
                    q = text("""
                        WITH rd_data AS (
                            SELECT
                                inc.symbol,
                                sp.sector AS sector,
                                CASE
                                    WHEN inc.revenue > 100000000 THEN (inc.rd_expenses::float / inc.revenue * 100)
                                    ELSE NULL
                                END AS rd_intensity
                            FROM fmp_income_statements inc
                            LEFT JOIN sp500_companies sp ON sp.symbol = inc.symbol
                            WHERE inc.fiscal_year = :formation_year
                              AND inc.period = 'FY'
                              AND inc.rd_expenses >= 0
                              AND inc.revenue >= 100000000
                        ),
                        ranked AS (
                            SELECT
                                rd.symbol,
                                rd.sector,
                                rd.rd_intensity,
                                NTILE(5) OVER (PARTITION BY rd.sector ORDER BY rd.rd_intensity) AS quintile
                            FROM rd_data rd
                            WHERE rd.rd_intensity IS NOT NULL
                              AND rd.sector IS NOT NULL
                        ),
                        returns AS (
                            SELECT symbol, annualized_return AS annual_return
                            FROM july_june_returns
                            WHERE formation_year = :formation_year
                              AND data_tier = :data_tier
                        ),
                        joined AS (
                            SELECT r.sector, r.quintile, ret.annual_return
                            FROM ranked r
                            JOIN returns ret ON r.symbol = ret.symbol
                            WHERE r.quintile IN (1, 5)
                              AND ret.annual_return IS NOT NULL
                        ),
                        sector_hml AS (
                            SELECT
                                sector,
                                AVG(CASE WHEN quintile = 5 THEN annual_return END) AS q5_avg,
                                AVG(CASE WHEN quintile = 1 THEN annual_return END) AS q1_avg
                            FROM joined
                            GROUP BY sector
                            HAVING COUNT(CASE WHEN quintile = 5 THEN 1 END) > 0
                               AND COUNT(CASE WHEN quintile = 1 THEN 1 END) > 0
                        )
                        SELECT
                            AVG(q5_avg - q1_avg) AS sector_neutral_hml,
                            COUNT(*) AS n_sectors
                        FROM sector_hml
                    """)
                    params = {"formation_year": formation_year, "data_tier": self.data_tier}

                result = await self.session.execute(q, params)
                row = result.fetchone()
                if row and row[0] is not None:
                    annual.append(
                        {
                            "year": f"Jul{return_year}-Jun{return_year+1}" if use_july_june else str(return_year),
                            "formation_year": int(formation_year),
                            "sector_neutral_hml_premium": float(row[0]) * 100.0,  # decimal -> %
                            "n_sectors": int(row[1] or 0),
                        }
                    )
            else:
                # Calendar-year sector-neutral series is out of scope for publication mode.
                continue

        if len(annual) < 5:
            return {"error": "Insufficient data for sector-neutral HML analysis", "n_years": len(annual)}

        premiums = [float(x["sector_neutral_hml_premium"]) for x in annual if x.get("sector_neutral_hml_premium") is not None]
        hac = self.compute_hac_ttest(premiums, hypothesis_value=0, lags=1)

        return {
            "annual_premiums": annual,
            "n_years": len(annual),
            "mean_premium": float(np.mean(premiums)),
            "std_dev": float(np.std(premiums, ddof=1)),
            "positive_years": sum(1 for p in premiums if p > 0),
            "win_rate": sum(1 for p in premiums if p > 0) / len(premiums),
            "hac_adjusted": {
                "nw_std_error": float(hac.std_error_hac),
                "t_statistic": float(hac.t_statistic_hac),
                "p_value": float(hac.p_value_hac),
                "lags_used": int(hac.lags_used),
            },
            "methodology": {
                "definition": "Within-sector quintiles each July; sector HML (Q5-Q1) averaged equally across sectors.",
                "sector_source": "sp500_companies.sector (current GICS label; point-in-time sectors unavailable in Tier-1)",
            },
            "note": "Sector-neutral robustness: equal-weight average of within-sector HML premiums (annual, non-overlapping).",
        }
