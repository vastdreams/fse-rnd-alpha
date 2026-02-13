"""AI-powered R&D analysis endpoints using DeepSeek 3.2 with concurrent analysis."""

import os
import asyncio
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import SP500Company, FMPIncomeStatement
from app.services.deepseek_client import DeepSeekClient

router = APIRouter()

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-954bb3759ed2458d863de843f0ae6f6a")


class CompanyAnalysis(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    analysis: dict
    confidence: float


class SectorAnalysis(BaseModel):
    sector: str
    analysis: dict


class ResearchInsights(BaseModel):
    executive_summary: Optional[str]
    key_findings: List[str]
    statistical_observations: Optional[dict]
    hypothesis_suggestions: List[str]
    next_steps: List[str]
    publication_angles: List[str]


async def get_company_rd_data(session: AsyncSession, symbol: str) -> dict:
    """Get comprehensive R&D data for a company."""
    company = await session.scalar(
        select(SP500Company).where(SP500Company.symbol == symbol)
    )
    if not company:
        return None
    result = await session.execute(
        select(FMPIncomeStatement)
        .where(FMPIncomeStatement.symbol == symbol)
        .where(FMPIncomeStatement.rd_expenses > 0)
        .order_by(FMPIncomeStatement.fiscal_year.desc())
    )
    statements = result.scalars().all()
    rd_by_year = []
    total_rd = 0
    for s in statements:
        intensity = (s.rd_expenses / s.revenue * 100) if s.revenue else 0
        rd_by_year.append({
            "year": s.fiscal_year, "rd_expense": s.rd_expenses,
            "revenue": s.revenue, "rd_intensity": intensity
        })
        total_rd += s.rd_expenses or 0
    avg_intensity = sum(r["rd_intensity"] for r in rd_by_year) / len(rd_by_year) if rd_by_year else 0
    return {
        "symbol": symbol, "name": company.name, "sector": company.sector,
        "total_rd_spend": total_rd, "avg_rd_intensity": avg_intensity,
        "years_with_rd": len(rd_by_year), "rd_by_year": rd_by_year
    }


@router.post("/company/{symbol}", response_model=CompanyAnalysis)
async def analyze_company(symbol: str, session: AsyncSession = Depends(get_session)):
    """AI-powered analysis of a company's R&D profile."""
    company_data = await get_company_rd_data(session, symbol.upper())
    if not company_data:
        raise HTTPException(404, f"Company {symbol} not found")
    if company_data["years_with_rd"] == 0:
        raise HTTPException(400, f"No R&D data available for {symbol}")
    async with DeepSeekClient(DEEPSEEK_API_KEY) as client:
        result = await client.analyze_rd_profile(company_data)
    return CompanyAnalysis(
        symbol=result.symbol, name=company_data["name"],
        sector=company_data["sector"], analysis=result.content, confidence=result.confidence
    )


@router.post("/batch", response_model=List[CompanyAnalysis])
async def batch_analyze_companies(symbols: List[str], session: AsyncSession = Depends(get_session)):
    """Concurrently analyze multiple companies."""
    if len(symbols) > 20:
        raise HTTPException(400, "Maximum 20 companies per batch")
    companies_data = []
    for symbol in symbols:
        data = await get_company_rd_data(session, symbol.upper())
        if data and data["years_with_rd"] > 0:
            companies_data.append(data)
    if not companies_data:
        raise HTTPException(400, "No valid companies with R&D data found")
    async with DeepSeekClient(DEEPSEEK_API_KEY, max_concurrent=10) as client:
        results = await client.batch_analyze_companies(companies_data)
    return [
        CompanyAnalysis(
            symbol=r.symbol,
            name=next((c["name"] for c in companies_data if c["symbol"] == r.symbol), None),
            sector=next((c["sector"] for c in companies_data if c["symbol"] == r.symbol), None),
            analysis=r.content, confidence=r.confidence
        )
        for r in results
    ]


@router.get("/sector/{sector}")
async def analyze_sector(sector: str, session: AsyncSession = Depends(get_session)):
    """Analyze R&D efficiency across a sector."""
    result = await session.execute(text("""
        SELECT i.symbol, c.name,
            AVG(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as avg_rd_intensity,
            SUM(i.rd_expenses) as total_rd_spend, COUNT(*) as years_of_data
        FROM fmp_income_statements i
        JOIN sp500_companies c ON i.symbol = c.symbol
        WHERE c.sector = :sector AND i.rd_expenses > 0 AND i.revenue > 0
        GROUP BY i.symbol, c.name ORDER BY avg_rd_intensity DESC LIMIT 15
    """), {"sector": sector})
    companies = [
        {"symbol": r.symbol, "name": r.name, "avg_rd_intensity": round(r.avg_rd_intensity, 2),
         "total_rd_spend": r.total_rd_spend, "years_of_data": r.years_of_data}
        for r in result.fetchall()
    ]
    if not companies:
        raise HTTPException(404, f"No companies found in sector: {sector}")
    async with DeepSeekClient(DEEPSEEK_API_KEY) as client:
        analysis = await client.analyze_sector_rd_efficiency(companies)
    return {"sector": sector, "companies_analyzed": len(companies), "companies": companies, "ai_analysis": analysis}


@router.get("/research-insights")
async def generate_research_insights(session: AsyncSession = Depends(get_session)):
    """Generate comprehensive research insights for publication."""
    trends_result = await session.execute(text("""
        SELECT fiscal_year as year, COUNT(DISTINCT symbol) as companies,
            AVG(rd_expenses / NULLIF(revenue, 0)) * 100 as avg_rd_intensity,
            SUM(rd_expenses) as total_rd_spend
        FROM fmp_income_statements WHERE rd_expenses > 0 AND revenue > 0
        GROUP BY fiscal_year ORDER BY fiscal_year
    """))
    rd_trends = [dict(r._mapping) for r in trends_result.fetchall()]
    sector_result = await session.execute(text("""
        SELECT c.sector, COUNT(DISTINCT i.symbol) as company_count,
            AVG(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as avg_rd_intensity
        FROM fmp_income_statements i JOIN sp500_companies c ON i.symbol = c.symbol
        WHERE i.rd_expenses > 0 AND i.revenue > 0 AND c.sector IS NOT NULL
        GROUP BY c.sector ORDER BY avg_rd_intensity DESC
    """))
    sector_comparison = [dict(r._mapping) for r in sector_result.fetchall()]
    top_result = await session.execute(text("""
        SELECT i.symbol, c.name, c.sector,
            AVG(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as avg_rd_intensity
        FROM fmp_income_statements i JOIN sp500_companies c ON i.symbol = c.symbol
        WHERE i.rd_expenses > 0 AND i.revenue > 0
        GROUP BY i.symbol, c.name, c.sector HAVING COUNT(*) >= 5
        ORDER BY avg_rd_intensity DESC LIMIT 20
    """))
    top_performers = [dict(r._mapping) for r in top_result.fetchall()]
    async with DeepSeekClient(DEEPSEEK_API_KEY) as client:
        insights = await client.generate_research_insights(rd_trends, sector_comparison, top_performers)
    return {
        "data_summary": {
            "years_analyzed": len(rd_trends), "sectors_analyzed": len(sector_comparison),
            "top_performers_count": len(top_performers)
        },
        "insights": insights
    }


@router.get("/cohort-recommendations")
async def get_cohort_recommendations(
    target_size: int = Query(50, ge=10, le=100),
    session: AsyncSession = Depends(get_session)
):
    """Get AI-recommended research cohort based on R&D profiles."""
    result = await session.execute(text("""
        WITH rd_stats AS (
            SELECT i.symbol, c.name, c.sector,
                AVG(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as avg_rd_intensity,
                SUM(i.rd_expenses) as total_rd_spend, COUNT(*) as years_of_data,
                STDDEV(i.rd_expenses / NULLIF(i.revenue, 0)) * 100 as rd_volatility
            FROM fmp_income_statements i JOIN sp500_companies c ON i.symbol = c.symbol
            WHERE i.rd_expenses > 0 AND i.revenue > 0
            GROUP BY i.symbol, c.name, c.sector HAVING COUNT(*) >= 10
        )
        SELECT * FROM rd_stats ORDER BY years_of_data DESC, avg_rd_intensity DESC LIMIT :limit
    """), {"limit": target_size * 2})
    candidates = [dict(r._mapping) for r in result.fetchall()]
    prompt = f"""Given these {len(candidates)} companies with R&D data, recommend an optimal research cohort of {target_size} companies for studying the relationship between R&D investment and shareholder returns.

Candidates (sorted by data completeness and R&D intensity):
"""
    for c in candidates[:30]:
        prompt += f"- {c['symbol']} ({c['sector']}): {c['avg_rd_intensity']:.1f}% intensity, {c['years_of_data']} years\n"
    prompt += f"""
Selection criteria should include:
1. Sector diversity (ensure all major sectors represented)
2. R&D intensity variation (mix of high, medium, low)
3. Data completeness (prefer more years)
4. Statistical representativeness

Return a JSON object with:
- selected_symbols: list of {target_size} recommended symbols
- selection_rationale: brief explanation
- sector_distribution: dict of sector -> count
- intensity_distribution: dict with high/medium/low counts"""
    async with DeepSeekClient(DEEPSEEK_API_KEY) as client:
        messages = [
            {"role": "system", "content": "You are a quantitative finance researcher selecting a statistically rigorous sample for academic study."},
            {"role": "user", "content": prompt}
        ]
        response = await client._chat_completion(messages, temperature=0.2, max_tokens=2000)
        recommendations = client._extract_json(response) if response else {"error": "Analysis failed"}
    return {
        "target_size": target_size, "candidates_evaluated": len(candidates),
        "recommendations": recommendations, "all_candidates": candidates[:target_size]
    }
