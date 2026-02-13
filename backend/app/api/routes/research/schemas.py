"""
PATH: backend/app/api/routes/research/schemas.py
PURPOSE: Pydantic request/response models for the research API.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class CohortCompanyResponse(BaseModel):
    symbol: str
    name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    years_with_data: int
    years_with_rd: int
    first_year: Optional[int]
    last_year: Optional[int]
    has_5yr_window: bool
    has_10yr_window: bool
    has_20yr_window: bool
    avg_rd_intensity: Optional[float]
    rd_profile: Optional[str]
    data_quality_score: Optional[float]


class CohortSummaryResponse(BaseModel):
    total_companies: int
    eligible_5yr: int
    eligible_10yr: int
    eligible_20yr: int
    avg_rd_intensity: float
    avg_quality_score: float
    by_sector: List[dict]
    by_rd_profile: dict


class QuintileResponse(BaseModel):
    quintile: int
    n_companies: int
    avg_rd_intensity: Optional[float]
    avg_return: Optional[float]
    total_return: Optional[float]
    volatility: Optional[float]
    sharpe_ratio: Optional[float]


class WindowResultResponse(BaseModel):
    window_type: str
    start_year: int
    end_year: int
    quintiles: List[QuintileResponse]
    rd_premium: float


class AnovaResultResponse(BaseModel):
    window_type: str
    period: str
    f_statistic: Optional[float]
    p_value: Optional[float]
    eta_squared: Optional[float]
    significant_005: bool
    significant_001: bool
    group_means: Optional[dict]
    high_low_diff: Optional[float]


class FactorPremiumResponse(BaseModel):
    year: int
    rd_premium: Optional[float]
    q1_return: Optional[float]
    q2_return: Optional[float]
    q3_return: Optional[float]
    q4_return: Optional[float]
    q5_return: Optional[float]


class ComputeJobResponse(BaseModel):
    status: str
    message: str


class PublicationSnapshotMetaResponse(BaseModel):
    id: str
    label: str
    is_active: bool
    return_convention: str
    data_tier: str
    built_at: datetime
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    notes: Optional[str] = None


class PublicationSnapshotResponse(BaseModel):
    meta: PublicationSnapshotMetaResponse
    payload: Dict[str, Any]


class BuildPublicationSnapshotRequest(BaseModel):
    label: str = "Publication Snapshot"
    return_convention: str = "july_june"
    data_tier: str = "tier1"
    notes: Optional[str] = None
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    set_active: bool = True


class DataQualityResponse(BaseModel):
    """Data quality metrics for research transparency."""
    total_sp500_companies: int
    companies_with_rd_data: int
    companies_with_return_data: int
    coverage_pct: float
    years_of_data: int
    min_year: int
    max_year: int
    rd_intensity_cap: float
    min_revenue_threshold: float
    outliers_capped_pct: float
    methodology_notes: List[str]


