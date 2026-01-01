"""
Portfolio API Routes

Provides endpoints for R&D ETF portfolio construction,
backtesting, benchmark comparison, and methodology transparency.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.api.deps import get_db
from app.services.portfolio_optimizer import PortfolioOptimizer
from app.services.rd_alpha_scorer import RDAlphaScorer, RDAlphaScore, SectorWeight
from app.services.market_forecasts import MarketForecaster
from app.services.universe_manager import UniverseManager

router = APIRouter()


# Response Models
class HoldingResponse(BaseModel):
    symbol: str
    name: str
    sector: str
    weight: float
    rd_intensity: float


class PerformanceResponse(BaseModel):
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float


class YearlyDataResponse(BaseModel):
    year: int
    portfolio_return: float
    benchmark_return: float
    excess_return: float


class BacktestResponse(BaseModel):
    period: str
    holdings: List[dict]
    portfolio_performance: PerformanceResponse
    benchmark_performance: PerformanceResponse
    excess_return: float
    yearly_data: List[YearlyDataResponse]


class SectorAllocationResponse(BaseModel):
    sector: str
    weight: float


class WindowResponse(BaseModel):
    window_id: str
    window_type: str
    start_year: int
    end_year: int
    label: str


# Endpoints
@router.get("/rd-etf", response_model=List[HoldingResponse])
async def get_rd_etf_holdings(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha", pattern="^(rd_alpha|quality_adjusted|highest_rd|balanced)$"),
    sector: Optional[str] = None,
    year: Optional[int] = Query(None, ge=1995, le=2030, description="Point-in-time year for ETF selection"),
    use_july_june: bool = Query(True, description="Use July-June returns for backtest alignment")
):
    """
    Get top R&D companies for ETF construction.
    
    Parameters:
    - n: Number of holdings (default 20)
    - method: Selection method (rd_alpha is now the default - recommended)
        - rd_alpha: Research-based sector-agnostic scoring (RECOMMENDED)
        - quality_adjusted: R&D intensity * data quality
        - highest_rd: Pure R&D intensity ranking
        - balanced: Diversified across sectors
    - sector: Optional sector filter
    - year: If provided, selects companies based on their R&D intensity in that specific year
    - use_july_june: Use July-June returns for backtest alignment (default True)
    
    PUBLICATION-GRADE (Dec 2025):
    - Default method changed to rd_alpha (research-based scoring)
    - Returns align with July-June convention for bias-free backtesting
    """
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    sectors = [sector] if sector else None
    
    if year:
        # Point-in-time selection for specific year
        holdings = await optimizer.select_top_rd_companies_for_year(
            as_of_year=year,
            n=n,
            method=method,
            sectors=sectors
        )
    else:
        holdings = await optimizer.select_top_rd_companies(
            n=n,
            method=method,
            sectors=sectors
        )
    
    return [
        HoldingResponse(
            symbol=h.symbol,
            name=h.name,
            sector=h.sector,
            weight=round(h.weight * 100, 2),
            rd_intensity=round(h.rd_intensity, 2)
        )
        for h in holdings
    ]


@router.get("/backtest")
async def backtest_portfolio(
    session: AsyncSession = Depends(get_db),
    start_year: int = Query(2010, ge=1995, le=2030),
    end_year: int = Query(2023, ge=1995, le=2030),
    n_holdings: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha"),
    sector: Optional[str] = None,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)")
):
    """
    Run backtest of R&D ETF strategy.
    
    Returns portfolio performance vs benchmark with yearly breakdown.
    
    PUBLICATION-GRADE (Dec 2025):
    - Default method changed to rd_alpha (research-based scoring)
    - Uses July-June returns by default (eliminates look-ahead bias)
    - Handles exits via cash-after-exit return construction; delisting uncertainty is addressed via sensitivity analysis
    """
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    sectors = [sector] if sector else None
    
    result = await optimizer.backtest_rd_etf(
        start_year=start_year,
        end_year=end_year,
        n_holdings=n_holdings,
        selection_method=method,
        sectors=sectors
    )
    
    return result


@router.get("/windows", response_model=List[WindowResponse])
async def get_available_windows(
    session: AsyncSession = Depends(get_db)
):
    """Get list of available time windows for analysis."""
    optimizer = PortfolioOptimizer(session)
    windows = await optimizer.get_available_windows()
    return windows


@router.get("/sectors")
async def get_sector_options(
    session: AsyncSession = Depends(get_db)
):
    """Get list of sectors available for filtering."""
    from sqlalchemy import select, func
    from app.db.models import ResearchCohort
    
    result = await session.execute(
        select(
            ResearchCohort.sector,
            func.count(ResearchCohort.symbol).label("count")
        )
        .where(ResearchCohort.sector.isnot(None))
        .group_by(ResearchCohort.sector)
        .order_by(func.count(ResearchCohort.symbol).desc())
    )
    
    sectors = result.fetchall()
    return [
        {"sector": s[0], "count": s[1]}
        for s in sectors
    ]


@router.get("/sector-allocation", response_model=List[SectorAllocationResponse])
async def get_portfolio_sector_allocation(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha"),
    year: Optional[int] = Query(None, ge=1995, le=2030),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)")
):
    """
    Get sector allocation of the R&D ETF portfolio.
    
    PUBLICATION-GRADE (Dec 2025): Default method changed to rd_alpha.
    """
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    
    if year:
        holdings = await optimizer.select_top_rd_companies_for_year(
            as_of_year=year, n=n, method=method
        )
    else:
        holdings = await optimizer.select_top_rd_companies(n=n, method=method)
    
    allocation = await optimizer.get_sector_allocation(holdings)
    
    return [
        SectorAllocationResponse(sector=a["sector"], weight=a["weight"])
        for a in allocation
    ]


@router.get("/forecast-vs-actual")
async def get_forecast_vs_actual(
    session: AsyncSession = Depends(get_db),
    year: int = Query(..., ge=1995, le=2030, description="Year to analyze"),
    n_holdings: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha"),
    sector: Optional[str] = None,
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)")
):
    """
    Compare forecasted returns vs actual returns for a specific year.
    
    For historical years, shows what the R&D premium model would have
    forecasted vs what actually happened.
    """
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    sectors = [sector] if sector else None
    
    result = await optimizer.get_forecast_vs_actual(
        as_of_year=year,
        n_holdings=n_holdings,
        method=method,
        sectors=sectors
    )
    
    return result


@router.get("/performance-comparison")
async def compare_performance_windows(
    session: AsyncSession = Depends(get_db),
    n_holdings: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha")
):
    """
    Compare R&D ETF performance across multiple time windows.
    Shows how the strategy would have performed in different periods.
    """
    optimizer = PortfolioOptimizer(session)
    
    # Test different 5-year windows
    windows = [
        (2000, 2004),
        (2005, 2009),
        (2010, 2014),
        (2015, 2019),
        (2019, 2023)
    ]
    
    comparisons = []
    for start, end in windows:
        try:
            result = await optimizer.backtest_rd_etf(
                start_year=start,
                end_year=end,
                n_holdings=n_holdings,
                selection_method=method
            )
            comparisons.append({
                "period": f"{start}-{end}",
                "portfolio_return": result["portfolio_performance"]["total_return"],
                "benchmark_return": result["benchmark_performance"]["total_return"],
                "excess_return": result["excess_return"],
                "sharpe": result["portfolio_performance"]["sharpe_ratio"]
            })
        except Exception as e:
            comparisons.append({
                "period": f"{start}-{end}",
                "error": str(e)
            })
    
    return comparisons


@router.get("/forecast")
async def get_current_forecast(
    session: AsyncSession = Depends(get_db),
    n_holdings: int = Query(20, ge=5, le=50),
    method: str = Query("rd_alpha"),
    use_july_june: bool = Query(True, description="Use July-June returns (Fama-French convention)")
):
    """
    Get forecast for current portfolio based on historical analysis.
    
    Uses historical quintile premium data to project expected returns.
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    optimizer = PortfolioOptimizer(session, use_july_june=use_july_june)
    
    # Get current holdings
    holdings = await optimizer.select_top_rd_companies(n=n_holdings, method=method)
    
    # Calculate average R&D intensity of portfolio
    avg_rd_intensity = sum(h.rd_intensity for h in holdings) / len(holdings) if holdings else 0
    
    # Baseline premium (publication-grade): derived from stored rolling-window results.
    # IMPORTANT: This is a **projection input**, not a guarantee or a prediction.
    from app.services.portfolio_optimizer import _get_baseline_rd_premium_pct
    return_convention = "july_june" if use_july_june else "calendar"
    expected_premium = await _get_baseline_rd_premium_pct(
        session,
        window_type="5yr",
        return_convention=return_convention,
        data_tier="tier1",
    )
    
    # Get recent benchmark return as base (align to return convention)
    from sqlalchemy import select, func
    from app.db.models import FMPAnnualReturn, JulyJuneReturn
    
    if use_july_june:
        max_result = await session.execute(
            select(func.max(JulyJuneReturn.formation_year))
            .where(JulyJuneReturn.data_tier == "tier1")
        )
        max_fy = max_result.scalar()
        if max_fy is not None:
            result = await session.execute(
                select(func.avg(JulyJuneReturn.annualized_return))
                .where(
                    JulyJuneReturn.data_tier == "tier1",
                    JulyJuneReturn.formation_year >= int(max_fy) - 4,
                    JulyJuneReturn.formation_year <= int(max_fy),
                    JulyJuneReturn.annualized_return.isnot(None),
                )
            )
            avg_raw = result.scalar()
            avg_market_return = float(avg_raw) if avg_raw is not None else 0.08
        else:
            avg_market_return = 0.08
    else:
        result = await session.execute(
            select(func.avg(FMPAnnualReturn.annual_return))
            .where(FMPAnnualReturn.year >= current_year - 5)
        )
        avg_raw = result.scalar()
        avg_market_return = float(avg_raw) if avg_raw is not None else 0.10
    
    return {
        "as_of": f"{current_year}",
        "holdings_count": len(holdings),
        "avg_rd_intensity": round(avg_rd_intensity, 2),
        "methodology": method,
        "forecast": {
            "expected_market_return": round(float(avg_market_return) * 100, 2),
            "expected_rd_premium": expected_premium,
            "expected_portfolio_return": round(float(avg_market_return) * 100 + expected_premium, 2),
            "confidence_level": "Based on snapshot-pinned historical analysis (see paper for sample window)",
            "risk_note": "Past performance does not guarantee future results"
        },
        "top_holdings": [
            {"symbol": h.symbol, "sector": h.sector, "rd_intensity": round(h.rd_intensity, 1)}
            for h in holdings[:5]
        ]
    }


# ==============================================================================
# New Transparency Endpoints (R&D Alpha Scorer)
# ==============================================================================

@router.get("/methodology")
async def get_selection_methodology():
    """
    Get complete documentation of the R&D Alpha selection formula.
    
    Returns the formula, component explanations, sector constraints,
    research citations, and parameter values for full transparency.
    """
    from app.services.rd_alpha_scorer import RDAlphaScorer
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    
    # Create a minimal scorer to get methodology (doesn't need session)
    class MockSession:
        pass
    
    # Get methodology from class
    scorer = RDAlphaScorer(None)  # type: ignore
    methodology = scorer.get_selection_methodology()
    
    return {
        "formula": methodology.formula,
        "formula_latex": methodology.formula_latex,
        "components": methodology.components,
        "sector_constraints": methodology.sector_constraints,
        "research_citations": methodology.research_citations,
        "parameters": methodology.parameters,
        "last_updated": methodology.last_updated,
    }


@router.get("/rd-alpha-holdings")
async def get_rd_alpha_holdings(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    year: Optional[int] = Query(None, ge=1995, le=2030)
):
    """
    Get R&D Alpha ETF holdings using the new sector-agnostic scoring formula.
    
    This uses the research-based selection formula that:
    - Caps R&D intensity by sector
    - Applies sector adjustment to prevent tech/biotech overweight
    - Includes momentum and quality factors
    - Normalizes by volatility
    - Uses point-in-time FY(T-1) financials for backtests
    
    ETF20 R&D ALPHA SELECTION:
    Formation date is July 1 of the given year.
    Holdings are selected using only data available at formation.
    """
    scorer = RDAlphaScorer(session)
    
    # Calculate scores for all candidates (returns tuple with eligibility result)
    all_scores, eligibility_result = await scorer.calculate_alpha_scores(
        universe="sp500",
        as_of_year=year
    )
    
    # Apply sector constraints and get final selection
    selected, sector_weights = await scorer.apply_sector_constraints(
        all_scores, n_holdings=n
    )
    
    response = {
        "holdings": [
            {
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "weight": round(s.weight * 100, 2),
                "rd_intensity": round(s.rd_intensity, 2),
                "rd_intensity_capped": round(s.rd_intensity_capped, 2),
                "sector_adjustment": round(s.sector_adjustment, 3),
                "momentum_factor": round(s.momentum_factor, 3),
                "quality_score": round(s.quality_score, 3),
                "final_score": round(s.final_score, 4),
                "rank": s.selection_rank,
                "fiscal_year_used": s.fiscal_year_used,
                "data_source": s.data_source,
            }
            for s in selected
        ],
        "sector_weights": [
            {
                "sector": sw.sector,
                "target_weight": round(sw.target_weight * 100, 1),
                "actual_weight": round(sw.actual_weight * 100, 1),
                "min_weight": round(sw.min_weight * 100, 1),
                "max_weight": round(sw.max_weight * 100, 1),
                "company_count": sw.company_count,
                "adjustment_needed": round(sw.adjustment_needed * 100, 1),
            }
            for sw in sector_weights
        ],
        "total_candidates": len(all_scores),
        "selected_count": len(selected),
    }
    
    # Add eligibility metadata if available
    if eligibility_result:
        response["eligibility"] = eligibility_result.to_meta_dict()
        response["eligibility"]["warnings"] = eligibility_result.warnings
    
    return response


@router.get("/sector-weights")
async def get_sector_weight_targets(
    session: AsyncSession = Depends(get_db),
    n: int = Query(20, ge=5, le=50),
    year: Optional[int] = Query(None, ge=1995, le=2030)
):
    """
    Get target vs actual sector weights for the R&D Alpha ETF.
    
    Shows how the portfolio is diversified and what adjustments
    would be needed to match target weights.
    """
    scorer = RDAlphaScorer(session)
    
    all_scores, _ = await scorer.calculate_alpha_scores(
        universe="sp500",
        as_of_year=year
    )
    
    _, sector_weights = await scorer.apply_sector_constraints(
        all_scores, n_holdings=n
    )
    
    return [
        {
            "sector": sw.sector,
            "target_weight": round(sw.target_weight * 100, 1),
            "actual_weight": round(sw.actual_weight * 100, 1),
            "min_weight": round(sw.min_weight * 100, 1),
            "max_weight": round(sw.max_weight * 100, 1),
            "company_count": sw.company_count,
            "adjustment_needed": round(sw.adjustment_needed * 100, 1),
            "status": (
                "overweight" if sw.actual_weight > sw.max_weight else
                "underweight" if sw.actual_weight < sw.min_weight else
                "on_target"
            ),
        }
        for sw in sector_weights
    ]


@router.get("/selection-candidates")
async def get_all_selection_candidates(
    session: AsyncSession = Depends(get_db),
    year: Optional[int] = Query(None, ge=1995, le=2030),
    limit: int = Query(100, ge=10, le=500)
):
    """
    Get all candidate companies with their R&D Alpha scores.
    
    Provides full transparency on why companies were or weren't selected.
    Useful for understanding the selection process.
    """
    scorer = RDAlphaScorer(session)
    
    all_scores, eligibility_result = await scorer.get_all_candidates_with_scores(
        as_of_year=year,
        limit=limit
    )
    
    response = {
        "candidates": [
            {
                "rank": s.selection_rank,
                "symbol": s.symbol,
                "name": s.name,
                "sector": s.sector,
                "rd_intensity": round(s.rd_intensity, 2),
                "rd_intensity_capped": round(s.rd_intensity_capped, 2),
                "sector_adjustment": round(s.sector_adjustment, 3),
                "momentum_factor": round(s.momentum_factor, 3),
                "quality_score": round(s.quality_score, 3),
                "volatility": round(s.volatility, 3),
                "final_score": round(s.final_score, 4),
                "years_of_data": s.years_of_data,
                "fiscal_year_used": s.fiscal_year_used,
                "data_source": s.data_source,
            }
            for s in all_scores
        ],
        "total_candidates": len(all_scores),
        "as_of_year": year,
    }
    
    # Add eligibility metadata if available
    if eligibility_result:
        response["eligibility"] = eligibility_result.to_meta_dict()
        response["eligibility"]["warnings"] = eligibility_result.warnings
    
    return response


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

