"""
PATH: backend/app/contracts/research.py
PURPOSE: W1 contracts for the investor platform redesign.

Design rules (locked 2026-07-12, see plan investor_platform_redesign):
- PIT everywhere: every rank-affecting value carries as_of_date (what period
  the value describes) AND available_date (when it became knowable). Rank jobs
  must never consume values with available_date > panel as_of.
- Missing = None/Unknown. No LLM-imputed numbers, ever.
- DeepSeek output kinds are ai_map / ai_gap / ai_runthrough — a DeepSeek run
  can never carry kind metric_value. Enforced by enum.
- Completeness ≠ attractiveness ≠ freshness: three separate axes.
- reviewer_passed can only be set through a FinalReview row (Cursor agent),
  never by the authoring pipeline.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# =============================================================================
# Sources & claims
# =============================================================================

class SourceKind(str, Enum):
    """Every allowed evidence source. IR/earnings kinds included by design."""

    SEC_10K = "10-K"
    SEC_20F = "20-F"
    SEC_10Q = "10-Q"
    SEC_8K = "8-K"
    EARNINGS_RELEASE = "earnings_release"
    IR_DECK = "ir_deck"
    IR_TRANSCRIPT = "ir_transcript"
    SHARADAR_PULL = "sharadar_pull"
    FMP_QUOTE = "fmp_quote"
    ALPHAVANTAGE_PULL = "alphavantage_pull"


class SourceSnapshot(BaseModel):
    """Immutable capture of a source document / data pull."""

    snapshot_id: str = Field(description="Stable id, e.g. sha256 of content + kind + fetched_at")
    kind: SourceKind
    ticker: str
    # PIT pair
    as_of_date: date = Field(description="Period the source describes (fiscal period end, quote time)")
    available_date: date = Field(description="Date the source became publicly knowable (filing/accepted date)")
    fetched_at: datetime
    locator: str = Field(description="SEC accession no. / API request id / URL")
    content_sha256: str
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _pit_sane(self) -> "SourceSnapshot":
        if self.available_date < self.as_of_date:
            raise ValueError(
                f"available_date {self.available_date} before as_of_date {self.as_of_date}"
            )
        return self


class EvidenceClaim(BaseModel):
    """One extracted fact bound to its source location. Numbers only come from here."""

    claim_id: str
    snapshot_id: str
    ticker: str
    field: str = Field(description="Schema slot, e.g. retention_value, rd_expense")
    value_text: str = Field(description="Verbatim excerpt or table cell as captured")
    value_numeric: Optional[float] = None
    operator: Optional[Literal["=", ">", ">=", "<", "<=", "~"]] = None
    unit: Optional[str] = None
    excerpt_locator: str = Field(description="Item/section + offset or table coordinates in the snapshot")
    extractor: str = Field(description="Deterministic extractor name+version that produced this claim")
    extracted_at: datetime


# =============================================================================
# Metric vector (every company, every family)
# =============================================================================

class MetricValue(BaseModel):
    """A single metric with full PIT provenance. None value == Unknown (never imputed)."""

    value: Optional[float] = None
    as_of_date: Optional[date] = None
    available_date: Optional[date] = None
    claim_ids: list[str] = Field(default_factory=list, description="Evidence claims backing this value")
    formula: Optional[str] = Field(default=None, description="Exact equation / code symbol")
    engine_version: Optional[str] = Field(default=None, description="Code hash of computing engine")

    @model_validator(mode="after")
    def _pit_pair(self) -> "MetricValue":
        if self.value is not None and (self.as_of_date is None or self.available_date is None):
            raise ValueError("A known metric value must carry as_of_date and available_date (PIT)")
        if (
            self.as_of_date is not None
            and self.available_date is not None
            and self.available_date < self.as_of_date
        ):
            raise ValueError("available_date before as_of_date")
        return self


class MetricVector(BaseModel):
    """Full per-ticker vector across the 8 families. Fields are Optional — missing stays missing."""

    ticker: str
    universe_version: str = Field(description="Versioned universe build this row belongs to")
    computed_at: datetime

    # --- Business FP (Layer 0)
    product_map_complete: Optional[bool] = None
    competitor_set_n: Optional[int] = None
    retention: MetricValue = Field(default_factory=MetricValue)
    concentration: MetricValue = Field(default_factory=MetricValue)
    moat_direction: Optional[Literal["widening", "stable", "eroding", "unknown"]] = None
    offering_quality_z: MetricValue = Field(default_factory=MetricValue)

    # --- AI Repricing / value (Paper-2)
    # The three lenses are frozen with the vector so historical DCF/book views
    # never silently substitute a newer panel's fair-value range.
    fair_px_lo: MetricValue = Field(default_factory=MetricValue)
    fair_px_med: MetricValue = Field(default_factory=MetricValue)
    fair_px_hi: MetricValue = Field(default_factory=MetricValue)
    mos_snapshot: MetricValue = Field(default_factory=MetricValue)
    mos_live: MetricValue = Field(default_factory=MetricValue)
    table20_pass_count: Optional[int] = None
    kill_active: Optional[bool] = None
    cohort: Optional[str] = None

    # --- R&D Alpha (Paper-1)
    rd_int: MetricValue = Field(default_factory=MetricValue)
    rd_gp: MetricValue = Field(default_factory=MetricValue)
    rd_mom: MetricValue = Field(default_factory=MetricValue)
    rd_capital: MetricValue = Field(default_factory=MetricValue)
    rd_prod: MetricValue = Field(default_factory=MetricValue)
    rd_cap_to_ev: MetricValue = Field(default_factory=MetricValue)

    # --- Quality / profitability
    gm: MetricValue = Field(default_factory=MetricValue)
    fcfm_sbc: MetricValue = Field(default_factory=MetricValue)
    roic: MetricValue = Field(default_factory=MetricValue)
    rule40: MetricValue = Field(default_factory=MetricValue)
    sbc_intensity: MetricValue = Field(default_factory=MetricValue)

    # --- Growth / investment
    rev_cagr: MetricValue = Field(default_factory=MetricValue)
    dilution_ann: MetricValue = Field(default_factory=MetricValue)
    runway_yrs: MetricValue = Field(default_factory=MetricValue)

    # --- Momentum (point-in-time)
    ret_1m: MetricValue = Field(default_factory=MetricValue)
    ret_3m: MetricValue = Field(default_factory=MetricValue)
    ret_12m: MetricValue = Field(default_factory=MetricValue)
    drawdown_from_peak: MetricValue = Field(default_factory=MetricValue)

    # --- Risk / red-flag
    ai_text_stance: MetricValue = Field(default_factory=MetricValue)
    float_fcf_share: MetricValue = Field(default_factory=MetricValue)
    carve_out: Optional[bool] = None
    route: Optional[Literal["fcf_positive", "pre_fcf", "carved_out"]] = None

    # --- Research completeness (separate axis)
    completeness: "ResearchCompleteness"

    @model_validator(mode="after")
    def _fair_value_band_is_ordered(self) -> "MetricVector":
        values = (self.fair_px_lo.value, self.fair_px_med.value, self.fair_px_hi.value)
        known = [value for value in values if value is not None]
        if known and (len(known) != 3 or any(value <= 0 for value in known) or not (values[0] <= values[1] <= values[2])):
            raise ValueError("Fair-value bands require finite positive low ≤ median ≤ high values")
        return self


class ResearchCompleteness(BaseModel):
    """Underwrite eligibility — never blended into attractiveness."""

    grade: Literal["A", "B", "C", "Incomplete"]
    filing_fetched: bool
    claims_n: int
    dcf_reproducible: bool
    overlay_fill_rate: float = Field(ge=0, le=1)
    competitor_map_filled: bool
    asof_freshness_days: Optional[int] = None
    stale: bool = Field(default=False, description="Past refresh SLA → blocks portfolio-ready")


# =============================================================================
# Recipes & ranking
# =============================================================================

RecipeId = Literal["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9"]


class RankRecipe(BaseModel):
    """A ranking combination. Formula must be shown on screen wherever a rank appears."""

    recipe_id: RecipeId
    name: str
    formula_human: str = Field(description="Plain-English one-liner shown above the table")
    formula_exact: str = Field(description="Exact combination expression over MetricVector fields")
    hard_filters: list[str] = Field(default_factory=list)
    axes: list[str] = Field(description="MetricVector fields consumed — each must have a LiteratureBind")
    benchmark_vs: str
    code_hash: Optional[str] = None
    custom: bool = Field(default=False, description="True for saved R9 custom recipes")


class RankedRow(BaseModel):
    """Output row of the rank service for one recipe run."""

    ticker: str
    recipe_id: RecipeId
    universe_version: str
    rank: int
    score: float
    contributions: dict[str, float] = Field(description="Per-axis contribution to the score")
    completeness_grade: Literal["A", "B", "C", "Incomplete"]
    freshness_ok: bool
    kill_active: Optional[bool] = Field(
        default=None,
        description="False = explicitly no kill; None = Unknown and must fail closed",
    )
    reviewer_passed: Optional[bool] = Field(
        default=None, description="Set ONLY from a FinalReview row; None = not yet reviewed"
    )


class GateEvaluation(BaseModel):
    """One Table-20 style gate result, replayable."""

    ticker: str
    gate_id: str
    passed: bool
    threshold: str
    observed: Optional[str] = None
    source_field: str
    claim_ids: list[str] = Field(default_factory=list)
    evaluated_at: datetime


# =============================================================================
# Audit / literature / AI / review
# =============================================================================

class LiteratureBind(BaseModel):
    """Research citation for a rank-moving axis. No bind → axis cannot ship in a recipe."""

    axis: str = Field(description="MetricVector field or recipe axis name")
    bib_key: str
    citation: str = Field(description="Short human cite, e.g. 'Lev & Sougiannis (1996)'")
    paper_section: Optional[str] = Field(default=None, description="Internal paper construct section")
    url_or_doi: Optional[str] = None


class AuditTrailEntry(BaseModel):
    """One row of the Audit tab trail for a metric on a ticker."""

    ticker: str
    axis: str
    metric: MetricValue
    snapshot_ids: list[str] = Field(default_factory=list)
    literature: list[LiteratureBind] = Field(default_factory=list)
    deepseek_run_id: Optional[str] = None
    final_review_id: Optional[str] = None
    generated_at: datetime


class DeepSeekOutputKind(str, Enum):
    """DeepSeek may ONLY produce these. metric_value is intentionally absent."""

    AI_MAP = "ai_map"
    AI_GAP = "ai_gap"
    AI_RUNTHROUGH = "ai_runthrough"
    AI_PEER_PROPOSE = "ai_peer_propose"
    AI_CONSISTENCY = "ai_consistency"


class DeepSeekAuditRun(BaseModel):
    """A continuous-audit job run. Structurally cannot author metric values."""

    run_id: str
    job: Literal["filing_map", "gap_audit", "peer_propose", "runthrough", "consistency"]
    ticker: Optional[str] = None
    output_kind: DeepSeekOutputKind
    output: dict = Field(description="Structured map/gaps/draft — consumed via confirm queue only")
    model: str = Field(default="deepseek-reasoner")
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: Literal["pending", "mapped", "flagged", "confirmed", "rejected"] = "pending"
    severity: Optional[Literal["low", "medium", "high"]] = None


class FinalReview(BaseModel):
    """Cursor-agent structure review. The only writer of reviewer_passed."""

    review_id: str
    ticker: Optional[str] = None
    recipe_id: Optional[RecipeId] = None
    trigger: Literal["top_k", "random_sample", "kill_flip", "high_severity_gap"]
    checklist: dict[str, bool] = Field(
        description="lineage_complete, no_llm_numbers, literature_present, deepseek_scope, structure_ia, sampling_logged, runthrough_usable, compliance"
    )
    passed: bool
    notes: Optional[str] = None
    reviewed_at: datetime
    reviewer: str = Field(default="cursor-agent")


# =============================================================================
# Book (portfolio)
# =============================================================================

class BookConstraint(BaseModel):
    kind: Literal[
        "max_name_pct",
        "max_sector_pct",
        "max_float_fcf_share",
        "max_incomplete_pct",
        "ban_kill_active",
        "ban_on_hold",
        "liquidity_floor",
    ]
    limit: Optional[float] = None
    enabled: bool = True


class BookHolding(BaseModel):
    ticker: str
    weight_pct: float = Field(ge=0, le=100)
    added_at: datetime
    override_reason: Optional[str] = Field(
        default=None, description="Required when adding despite a blocker (Incomplete/stale/kill)"
    )

    @model_validator(mode="after")
    def _normalize_identity_and_override(self) -> "BookHolding":
        self.ticker = self.ticker.strip().upper()
        if not self.ticker:
            raise ValueError("Ticker is required")
        if self.override_reason is not None:
            self.override_reason = self.override_reason.strip()
            if not self.override_reason:
                raise ValueError("override_reason must contain non-whitespace text")
        return self


class SavedBook(BaseModel):
    """Server-persisted book. Starts empty — never auto-seeded."""

    book_id: str
    user_id: str
    name: str
    holdings: list[BookHolding] = Field(default_factory=list)
    constraints: list[BookConstraint] = Field(default_factory=list)
    recipe_id: Optional[RecipeId] = None
    universe_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    research_only_ack: bool = Field(
        default=True, description="Watermark: research only, not investment advice"
    )

    @model_validator(mode="after")
    def _weights_sane(self) -> "SavedBook":
        total = sum(h.weight_pct for h in self.holdings)
        if self.holdings and total > 100.0001:
            raise ValueError(f"Weights sum to {total:.2f}% > 100%")
        return self


# =============================================================================
# Close-call waterfall → research BUY / HOLD stance (MedTwin-style)
# =============================================================================

StageStatus = Literal["known", "unknown", "partial"]
ResearchStance = Literal["BUY", "HOLD", "WATCH", "OUT", "UNKNOWN"]
StanceConfidence = Literal["high", "med", "low", "none"]

# Shared FE/BE taxonomy for /api/universe/rank row auditors (finance fail-closed).
RankViolationCode = Literal[
    "VS_MEDIAN_MISMATCH",
    "FAIR_BAND_ORDER",
    "FAIR_BAND_ZONE_CONTRADICTION",
    "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
    "SCORE_WITHOUT_DRIVERS",
    "NON_FINITE_METRIC",
]
RANK_VIOLATION_CODES: tuple[str, ...] = (
    "VS_MEDIAN_MISMATCH",
    "FAIR_BAND_ORDER",
    "FAIR_BAND_ZONE_CONTRADICTION",
    "MOS_SIGN_CONTRADICTS_PRICE_VS_TARGET",
    "SCORE_WITHOUT_DRIVERS",
    "NON_FINITE_METRIC",
)


class WaterfallClaim(BaseModel):
    """One grounded fact in a waterfall stage. No invented numbers."""

    claim_id: str
    field: str
    value_text: str
    value_numeric: Optional[float] = None
    locator: Optional[str] = Field(default=None, description="URL / accession / formula id")
    as_of_date: Optional[date] = None


class WaterfallStage(BaseModel):
    """One layer of the close-call waterfall (stats-engine style L0…Ln)."""

    id: str
    title: str
    status: StageStatus
    score: Optional[float] = Field(default=None, ge=0, le=10, description="None = unknown")
    summary: str
    claims: list[WaterfallClaim] = Field(default_factory=list)
    unknown_reason: Optional[str] = None


class RoiRun(BaseModel):
    """One weighted ROI run feeding the aggregate stance score."""

    id: str
    label: str
    weight: float = Field(gt=0)
    score: Optional[float] = Field(default=None, ge=0, le=10)
    contributions: dict[str, float] = Field(default_factory=dict)
    unknown_axes: list[str] = Field(default_factory=list)
    note: str = ""


class PrecedenceExample(BaseModel):
    """Paper / desk precedent that the stance must clear (or fail explicitly)."""

    id: str
    label: str
    rule: str
    matched: Optional[bool] = Field(
        default=None, description="None = cannot evaluate (unknown inputs)"
    )
    evidence: str
    gate_kind: Literal["hard", "advisory"] = Field(
        default="hard",
        description="advisory = shown for transparency but not in buy_ok",
    )
    opinion: bool = Field(
        default=False, description="Must stay false — precedence is data-evaluated"
    )


class StanceAggregate(BaseModel):
    """Final research stance. BUY only when confidence gates clear."""

    score: Optional[float] = Field(default=None, ge=0, le=100)
    confidence: StanceConfidence
    stance: ResearchStance
    horizon_years: Optional[Literal[1, 2, 3]] = None
    horizon_note: Optional[str] = None
    implied_ann_return: Optional[float] = Field(
        default=None, description="Convergence math if gap closes over horizon_years"
    )
    blockers: list[str] = Field(default_factory=list)
    flowchart: list[dict] = Field(
        default_factory=list,
        description=(
            "Ordered decision nodes: {id, label, result, detail, gate_kind, "
            "data_fields, formula_ids, opinion, references}"
        ),
    )
    precedence_examples: list[PrecedenceExample] = Field(default_factory=list)
    decision_chain_id: str = "D_STANCE_BUY"
    decision_provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="First-principles provenance blob from decision_chains.json",
    )
    engine_version: str = "close_call_v1"
    watermark: str = (
        "Research stance from the close-call waterfall — not a broker recommendation."
    )


class CloseCallWaterfall(BaseModel):
    """Per-ticker structured close-call analysis → weighted ROI → stance."""

    ticker: str
    universe_version: str
    computed_at: datetime
    stages: list[WaterfallStage]
    roi_runs: list[RoiRun]
    aggregate: StanceAggregate


MetricVector.model_rebuild()
