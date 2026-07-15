"""
PATH: backend/app/contracts/company_reports.py
PURPOSE: Frozen contracts for two-page institutional company briefs.

Design rules (mirrors research.py):
- Every value carries PIT dates + provenance class. Missing = None = Unknown,
  never imputed.
- A published snapshot is immutable: canonical JSON + sha256; any change is a
  new snapshot.
- Section budgets are validation errors, not layout hints — overflow can never
  silently create a third page.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, model_validator

TEMPLATE_VERSION = "brief_2p_v1"

# Per-section word budgets for the fixed A4 layout. Keys are section_ids.
SECTION_WORD_BUDGETS: dict[str, int] = {
    "variant_perception": 60,
    "business_model": 130,
    "industry_map": 120,
    "moat": 120,
    "financial_trends": 90,
    "thesis": 150,
    "catalysts": 90,
    "consensus_vs_internal": 150,
    "estimate_revisions": 90,
    "management_governance": 150,
    "gates_factor_context": 110,
    "risks_falsification": 170,
    "sizing": 90,
    "methodology": 110,
}
PAGE1_SECTIONS = (
    "variant_perception",
    "business_model",
    "industry_map",
    "moat",
    "financial_trends",
    "thesis",
    "catalysts",
)
PAGE2_SECTIONS = (
    "consensus_vs_internal",
    "estimate_revisions",
    "management_governance",
    "gates_factor_context",
    "risks_falsification",
    "sizing",
    "methodology",
)
MAX_CITATIONS = 40
MAX_METRICS_PER_SECTION = 14
MAX_SCENARIOS = 4


class ProvenanceClass(str, Enum):
    """Where a report value comes from. Rendered next to the value."""

    SEALED = "sealed"                       # immutable universe evidence
    CURRENT_OVERLAY = "current_overlay"     # live/current data with visible date
    LICENSED_CONSENSUS = "licensed_consensus"
    ANALYST = "analyst"                     # authored narrative, reviewed
    MODEL = "model"                         # reproducible internal computation


class ReportCitation(BaseModel):
    """One numbered source in the compact citation block."""

    cite_id: str = Field(description="Render key, e.g. '1', '2'")
    provenance: ProvenanceClass
    title: str
    locator: str = Field(description="SEC accession / API request id / URL / claim_id")
    source_id: Optional[str] = Field(
        default=None, description="claim_id / snapshot_id / consensus snapshot id"
    )
    as_of_date: Optional[date] = None
    available_date: Optional[date] = None
    url: Optional[str] = None

    @model_validator(mode="after")
    def _pit(self) -> "ReportCitation":
        if (
            self.as_of_date is not None
            and self.available_date is not None
            and self.available_date < self.as_of_date
        ):
            raise ValueError("available_date before as_of_date")
        return self


class ReportMetric(BaseModel):
    """A single displayed number. None value renders as Unknown."""

    label: str
    value: Optional[float] = None
    display: Optional[str] = Field(
        default=None, description="Pre-formatted display string when float is unsuitable"
    )
    unit: Optional[str] = None
    provenance: ProvenanceClass
    as_of_date: Optional[date] = None
    cite_ids: list[str] = Field(default_factory=list)
    methodology: Optional[str] = None

    @model_validator(mode="after")
    def _known_needs_citation(self) -> "ReportMetric":
        if (self.value is not None or self.display is not None) and not self.cite_ids:
            raise ValueError(f"Metric '{self.label}' has a value but no citation")
        return self


class ReportScenario(BaseModel):
    """Consensus or internal bull/base/bear underwriting row."""

    name: str = Field(description="consensus | bull | base | bear")
    provenance: ProvenanceClass
    rev_growth: Optional[float] = None
    margin: Optional[float] = None
    fair_px: Optional[float] = None
    implied_return: Optional[float] = None
    cite_ids: list[str] = Field(default_factory=list)
    note: Optional[str] = None


class ReportSection(BaseModel):
    """One titled block on a page. Body is plain text/markdown-lite."""

    section_id: str
    title: str
    body: str = ""
    metrics: list[ReportMetric] = Field(default_factory=list)
    scenarios: list[ReportScenario] = Field(default_factory=list)
    cite_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _budgets(self) -> "ReportSection":
        budget = SECTION_WORD_BUDGETS.get(self.section_id)
        if budget is None:
            raise ValueError(f"Unknown section_id '{self.section_id}'")
        n_words = len(self.body.split())
        if n_words > budget:
            raise ValueError(
                f"Section '{self.section_id}' body has {n_words} words; budget {budget}"
            )
        if len(self.metrics) > MAX_METRICS_PER_SECTION:
            raise ValueError(f"Section '{self.section_id}' exceeds metric budget")
        if len(self.scenarios) > MAX_SCENARIOS:
            raise ValueError(f"Section '{self.section_id}' exceeds scenario budget")
        # Narrative prose must cite; metric-only sections cite per metric.
        if self.body.strip() and not self.cite_ids:
            raise ValueError(f"Section '{self.section_id}' narrative has no citations")
        return self


class ReportStatus(str, Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    REVIEWED = "reviewed"
    PUBLISHED = "published"


class CompanyReportSnapshot(BaseModel):
    """The full immutable two-page brief for one company."""

    snapshot_id: str
    ticker: str
    universe_version: str
    template_version: str = TEMPLATE_VERSION
    engine_version: str
    created_at: datetime
    as_of_date: date
    status: ReportStatus = ReportStatus.DRAFT

    # Header facts
    company_name: Optional[str] = None
    exchange: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    stance: Optional[str] = None
    price: Optional[float] = None
    price_as_of: Optional[date] = None
    fair_px_lo: Optional[float] = None
    fair_px_med: Optional[float] = None
    fair_px_hi: Optional[float] = None
    mos_live: Optional[float] = None
    implied_ann_return: Optional[float] = None
    horizon_years: Optional[int] = None
    market_cap: Optional[float] = None

    page1: list[ReportSection] = Field(default_factory=list)
    page2: list[ReportSection] = Field(default_factory=list)
    citations: list[ReportCitation] = Field(default_factory=list)
    disclosures: list[str] = Field(default_factory=list)

    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    @model_validator(mode="after")
    def _structure(self) -> "CompanyReportSnapshot":
        p1_ids = [s.section_id for s in self.page1]
        p2_ids = [s.section_id for s in self.page2]
        if p1_ids != list(PAGE1_SECTIONS):
            raise ValueError(f"page1 sections must be exactly {list(PAGE1_SECTIONS)}, got {p1_ids}")
        if p2_ids != list(PAGE2_SECTIONS):
            raise ValueError(f"page2 sections must be exactly {list(PAGE2_SECTIONS)}, got {p2_ids}")
        if len(self.citations) > MAX_CITATIONS:
            raise ValueError(f"{len(self.citations)} citations exceeds cap {MAX_CITATIONS}")
        known = {c.cite_id for c in self.citations}
        if len(known) != len(self.citations):
            raise ValueError("Duplicate cite_id in citations")
        referenced: set[str] = set()
        for section in [*self.page1, *self.page2]:
            referenced.update(section.cite_ids)
            for metric in section.metrics:
                referenced.update(metric.cite_ids)
            for scenario in section.scenarios:
                referenced.update(scenario.cite_ids)
        dangling = referenced - known
        if dangling:
            raise ValueError(f"Sections reference unknown cite_ids: {sorted(dangling)}")
        if not self.disclosures:
            raise ValueError("A report must carry disclosures")
        return self


def canonical_report_json(snapshot: CompanyReportSnapshot) -> str:
    """Deterministic serialization used for hashing and storage."""
    payload = snapshot.model_dump(mode="json")
    # The hash covers content, not workflow state. snapshot_id is derived from
    # this hash, so it cannot participate in it.
    for volatile in ("snapshot_id", "status", "reviewed_by", "reviewed_at"):
        payload.pop(volatile, None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def report_content_sha256(snapshot: CompanyReportSnapshot) -> str:
    return hashlib.sha256(canonical_report_json(snapshot).encode()).hexdigest()
