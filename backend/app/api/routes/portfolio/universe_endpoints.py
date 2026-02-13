"""
PATH: backend/app/api/routes/portfolio/universe_endpoints.py
PURPOSE: Universe management and forecast distribution endpoints.
WHY: Separated from core_endpoints to respect the ~300-line budget.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.portfolio_optimizer import PortfolioOptimizer
from app.services.market_forecasts import MarketForecaster
from app.services.universe_manager import UniverseManager

router = APIRouter()


@router.get("/sp500-forecast")
async def get_sp500_consensus_forecast(
    years_forward: int = Query(10, ge=1, le=20),
    include_historical: bool = Query(True)
):
    """
    Get S&P 500 consensus forecasts from major investment banks.
    
    Returns forecasts with full source attribution for transparency.
    Includes Goldman Sachs, JP Morgan, Morgan Stanley, and Bank of America.
    """
    forecaster = MarketForecaster()
    
    response = forecaster.get_sp500_forecast(
        years_forward=years_forward,
        include_historical=include_historical
    )
    
    return {
        "forecasts": [
            {
                "year": f.year,
                "level_low": f.level_low,
                "level_mid": f.level_mid,
                "level_high": f.level_high,
                "return_low": f.return_low,
                "return_mid": f.return_mid,
                "return_high": f.return_high,
                "is_forecast": f.is_forecast,
                "source": f.source,
                "notes": f.notes,
            }
            for f in response.forecasts
        ],
        "sources": [
            {
                "name": s.name,
                "division": s.division,
                "frequency": s.frequency,
                "last_update": s.last_update,
                "methodology": s.methodology,
            }
            for s in response.sources
        ],
        "base_year": response.base_year,
        "base_level": response.base_level,
        "methodology_summary": response.methodology_summary,
        "last_updated": response.last_updated,
        "disclaimer": response.disclaimer,
    }


@router.get("/universes")
async def get_available_universes(
    session: AsyncSession = Depends(get_db)
):
    """
    Get information on available stock universes.
    
    Currently supports S&P 500, Russell 1000, and Russell 3000.
    """
    manager = UniverseManager(session)
    universes = await manager.get_available_universes()
    
    return [
        {
            "code": u.code,
            "name": u.name,
            "description": u.description,
            "approximate_size": u.approximate_size,
            "market_cap_threshold": u.market_cap_threshold,
            "reconstitution": u.reconstitution,
            "index_provider": u.index_provider,
            "actual_count": u.actual_count,
            "with_rd_data": u.with_rd_data,
        }
        for u in universes
    ]


@router.get("/universe-sectors")
async def get_universe_sector_breakdown(
    session: AsyncSession = Depends(get_db),
    universe: str = Query("sp500", pattern="^(sp500|russell1000|russell3000|all)$")
):
    """
    Get sector breakdown for a specific universe.
    
    Shows target weights and actual coverage from database.
    """
    manager = UniverseManager(session)
    breakdowns = await manager.get_universe_sectors(universe)
    
    return [
        {
            "sector": b.sector,
            "target_weight": round(b.target_weight * 100, 1),
            "actual_count": b.actual_count,
            "with_rd_data": b.with_rd_data,
            "coverage_pct": round(b.coverage_pct, 1),
        }
        for b in breakdowns
    ]


# ==============================================================================
# Forecast Distribution Endpoint (ETF20 R&D Alpha)
# ==============================================================================

@router.get("/forecast-distribution")
async def get_forecast_distribution(
    session: AsyncSession = Depends(get_db),
    n_holdings: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha"),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)")
):
    """
    Get ETF20 R&D Alpha expected return distribution with probability bands.
    
    Returns:
    - Expected return with p10/p50/p90 bands
    - Market baseline scenarios (low/mid/high)
    - Historical R&D premium dispersion
    - Confidence metrics and methodology
    
    This is a PROJECTION tool, not a prediction. Past performance does not guarantee future results.
    """
    from datetime import datetime
    from sqlalchemy import select, func
    from app.db.models import RollingWindowResult, FamaFrenchFactor
    
    current_year = datetime.now().year
    return_convention = "july_june" if use_july_june else "calendar"
    
    # Get market forecaster scenarios
    forecaster = MarketForecaster()
    market_forecast = forecaster.get_sp500_forecast(years_forward=5, include_historical=False)
    
    # Extract 5-year forward scenarios
    market_scenarios = {
        "low": None,
        "mid": None,
        "high": None,
    }
    for f in market_forecast.forecasts:
        if f.is_forecast and f.year == current_year + 5:
            market_scenarios["low"] = f.return_low
            market_scenarios["mid"] = f.return_mid
            market_scenarios["high"] = f.return_high
            break
    
    # Fallback market return assumptions if no forecast data
    if market_scenarios["mid"] is None:
        market_scenarios = {"low": 4.0, "mid": 7.0, "high": 10.0}
    
    # Get historical R&D premium from rolling window results
    premium_result = await session.execute(
        select(
            RollingWindowResult.quintile,
            func.avg(RollingWindowResult.avg_return).label("avg_ret"),
            func.stddev(RollingWindowResult.avg_return).label("std_ret"),
        )
        .where(
            RollingWindowResult.return_convention == return_convention,
            RollingWindowResult.data_tier == "tier1",
            RollingWindowResult.quintile.in_([1, 5]),
            RollingWindowResult.avg_return.isnot(None),
        )
        .group_by(RollingWindowResult.quintile)
    )
    
    premium_data = {int(r[0]): {"avg": float(r[1]), "std": float(r[2]) if r[2] else 0} for r in premium_result.fetchall()}
    
    # Calculate R&D premium and its dispersion
    if 1 in premium_data and 5 in premium_data:
        base_premium = premium_data[5]["avg"] - premium_data[1]["avg"]
        # Premium dispersion: combine Q5 and Q1 volatility
        premium_std = (premium_data[5].get("std", 0) ** 2 + premium_data[1].get("std", 0) ** 2) ** 0.5
    else:
        # Fallback: derive inputs from the active publication snapshot (pins assumptions to the frozen dataset).
        from app.db.models import PublicationSnapshot

        snapshot_payload = None
        try:
            snap_res = await session.execute(
                select(PublicationSnapshot.payload)
                .where(PublicationSnapshot.is_active == True)  # noqa: E712
                .order_by(PublicationSnapshot.built_at.desc())
                .limit(1)
            )
            snapshot_payload = snap_res.scalar_one_or_none()
        except Exception:
            snapshot_payload = None

        base_premium = None
        premium_std = None

        if isinstance(snapshot_payload, dict):
            stats = snapshot_payload.get("publication_stats")
            if isinstance(stats, dict):
                stats_5yr = stats.get("5yr")
                if isinstance(stats_5yr, dict):
                    ttest = stats_5yr.get("ttest_high_vs_low")
                    if isinstance(ttest, dict) and isinstance(ttest.get("mean_difference"), (int, float)):
                        base_premium = float(ttest["mean_difference"])

            annual = snapshot_payload.get("annual_hml_premium")
            if isinstance(annual, dict) and isinstance(annual.get("std_dev"), (int, float)):
                premium_std = float(annual["std_dev"])

        # If we still can't derive a premium, return a clear error instead of a magic number.
        if not isinstance(base_premium, (int, float)) or not isinstance(premium_std, (int, float)):
            return {
                "error": (
                    "Forecast distribution unavailable: missing rolling-window premium series and no active "
                    "publication snapshot could be found. Recompute research outputs or activate a snapshot."
                )
            }
    
    # Calculate expected return distribution
    # E[R] = Market Return + R&D Premium
    # Distribution uses market scenarios × premium dispersion
    
    def calc_percentile(market_ret: float, premium: float, premium_std: float, z_score: float) -> float:
        """Calculate return at a given z-score."""
        return market_ret + premium + z_score * premium_std
    
    # p10 = low market + premium - 1.28σ
    # p50 = mid market + premium
    # p90 = high market + premium + 1.28σ
    
    distribution = {
        "p10": {
            "expected_return": round(market_scenarios["low"] + base_premium - 1.28 * premium_std, 2),
            "market_scenario": "bearish",
            "premium_scenario": "below_average",
        },
        "p50": {
            "expected_return": round(market_scenarios["mid"] + base_premium, 2),
            "market_scenario": "base_case",
            "premium_scenario": "average",
        },
        "p90": {
            "expected_return": round(market_scenarios["high"] + base_premium + 1.28 * premium_std, 2),
            "market_scenario": "bullish",
            "premium_scenario": "above_average",
        },
    }
    
    # Get current holdings for context
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    holdings = await optimizer.select_top_rd_companies(n=n_holdings, method=method)
    avg_rd_intensity = sum(h.rd_intensity for h in holdings) / len(holdings) if holdings else 0
    
    return {
        "as_of": str(current_year),
        "methodology": method,
        "holdings_count": len(holdings),
        "avg_rd_intensity": round(avg_rd_intensity, 2),
        "distribution": distribution,
        "components": {
            "market_baseline": {
                "low": market_scenarios["low"],
                "mid": market_scenarios["mid"],
                "high": market_scenarios["high"],
                "source": "Investment bank consensus (GS, JPM, MS, BAC)",
            },
            "rd_premium": {
                "expected": round(base_premium, 2),
                "historical_std": round(premium_std, 2),
                "source": "Historical Q5-Q1 spread (Tier 1 data)",
            },
        },
        "confidence": {
            "level": "moderate",
            "note": "Based on historical Tier-1 data; point-in-time constituent spans are enforced where available",
            "caveats": [
                "Past performance does not guarantee future results",
                "Premium may vary significantly year-to-year",
                "Market regime changes can affect R&D premium persistence",
            ],
        },
        "methodology_summary": (
            f"Expected return = Market baseline + R&D premium. "
            f"The R&D premium of {round(base_premium, 1)}% annually is derived from historical "
            f"Q5-Q1 spread analysis using {return_convention} returns. "
            f"Distribution bands incorporate market scenario uncertainty and premium dispersion."
        ),
        "disclaimer": (
            "This is a projection tool for educational purposes only. "
            "It is not investment advice. Past performance does not guarantee future results. "
            "Actual returns may differ materially from projections."
        ),
    }
