"""
PATH: backend/app/api/routes/portfolio/core_endpoints.py
PURPOSE: Core ETF portfolio endpoints — holdings, backtest, windows, sectors, allocation, forecast, performance comparison.
WHY: Extracted from monolithic portfolio.py to keep each module under ~300 lines.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.services.portfolio_optimizer import PortfolioOptimizer
from app.api.routes.portfolio.models import (
    HoldingResponse,
    WindowResponse,
    SectorAllocationResponse,
)

router = APIRouter()


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
