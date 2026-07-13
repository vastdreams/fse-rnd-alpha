#!/usr/bin/env python3
"""
PATH: scripts/build_universe.py
PURPOSE: W2a universe builder — populate metric_vectors (+ source_snapshots,
evidence_claims, literature_binds, rank_recipes) for the FULL universe.

Data sources (facts only — no LLM anywhere in this pipeline):
  1. data/saas_ai_repricing/fundamental_value_run.csv
       347-name panel (paper universe: US software/SaaS incl. pre-FCF route).
       Fundamentals as-of `date_l`; conservative PIT lag applied (see PIT notes).
  2. data/saas_ai_repricing/first_principles_overlay.csv
       32 names with 10-K claims: NRR (verbatim), customer concentration,
       AI text stance, filing accession + filing_date (true available_date).
  3. backend/app/data/saas_portfolio_bundle.json
       Gate evaluations, kill criteria, payments/fintech carve-out, paper tiers.
  4. Sharadar SEP (Nasdaq Data Link) — daily adjusted closes for momentum
       (ret_1m/3m/12m, drawdown) and live price → mos_live recompute.

PIT notes:
  * Panel fundamentals: as_of = date_l. available_date = filing_date where the
    overlay provides an accession; otherwise date_l + PANEL_PIT_LAG_DAYS (90) —
    a documented CONSERVATIVE assumption (10-K/Q filing lag), never optimistic.
  * Prices: as_of = available_date = trade date.
  * mos_live: fair value is snapshot-dated (date_l-derived); price is live.
    Both dates are carried; the UI must show the dual as-of.

Anti-hallucination: every numeric written here traces to a CSV cell, bundle
field, or SEP row via an EvidenceClaim with a locator. Missing stays None.

Usage:
  backend/.venv/bin/python scripts/build_universe.py [--skip-prices] [--version V] [--activate]

Each invocation creates a new immutable, content-addressed universe version.
Reusing a version name is rejected rather than overwriting prior research.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.contracts.recipes import LITERATURE_BINDS, PRESET_RECIPES  # noqa: E402
from app.contracts.research import (  # noqa: E402
    MetricValue,
    MetricVector,
    ResearchCompleteness,
)
from app.services.rank_service.engine import robust_z  # noqa: E402

PANEL_CSV = REPO / "data/saas_ai_repricing/fundamental_value_run.csv"
OVERLAY_CSV = REPO / "data/saas_ai_repricing/first_principles_overlay.csv"
BUNDLE_JSON = REPO / "backend/app/data/saas_portfolio_bundle.json"
FILINGS_CACHE = REPO / "data" / "filings_cache"

PANEL_PIT_LAG_DAYS = 90  # conservative filing lag when no accession-dated claim exists
STALE_SLA_DAYS = 200  # fundamentals older than this vs today → stale flag
ENGINE_VERSION = "universe_builder@w2c"

# Kill flags: active/inactive states must be explicitly reviewed. A missing
# entry remains None/UNKNOWN and the rank engine fails closed; it is never
# converted into a synthetic False merely because the bundle has no trigger.
# Active trigger is evidenced for WDAY (MODEL10_AI_AUDIT 2026-07-12: NDR breach).
KILL_ACTIVE = {"WDAY": True, "FRSH": False, "DOCU": False, "PCTY": False}


def release_sha() -> str:
    value = os.environ.get("RELEASE_SHA", "").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SystemExit(
            "RELEASE_SHA must be the full 40-character committed source SHA before building a universe."
        )
    return value

SEP_URL = "https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP"


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def filing_content_sha(ticker: str, accession: str, overlay_row) -> tuple[str, str]:
    """Hash cached filing text when available; otherwise hash captured metadata.

    The note makes the distinction explicit so an absent local filing is never
    misrepresented as a full-document content hash.
    """

    text_path = FILINGS_CACHE / f"{ticker}.txt"
    if text_path.exists():
        return sha_bytes(text_path.read_bytes()), "full cached filing text"
    metadata = {
        "ticker": ticker,
        "accession": accession,
        "filing_date": str(overlay_row.get("filing_date")),
        "filing_url": str(overlay_row.get("filing_url")),
    }
    return sha(canonical_json(metadata)), "captured filing metadata only; full text unavailable"


def build_manifest(
    *,
    prices: pd.DataFrame | None,
    skip_prices: bool,
    source_sha: str,
) -> tuple[str, dict]:
    """Return a complete, stable manifest and its content hash.

    The requested universe version is derived from every local source plus the
    exact SEP rows used for price-based metrics. That makes a rebuild with new
    inputs a distinct snapshot rather than a silent mutation of today's run.
    """

    source_hashes = {
        str(PANEL_CSV.relative_to(REPO)): file_sha(PANEL_CSV),
        str(OVERLAY_CSV.relative_to(REPO)): file_sha(OVERLAY_CSV),
        str(BUNDLE_JSON.relative_to(REPO)): file_sha(BUNDLE_JSON),
    }
    price_hash = None
    if prices is not None:
        rows = [
            {
                "ticker": str(row.ticker),
                "date": str(row.date),
                "closeadj": None if pd.isna(row.closeadj) else float(row.closeadj),
            }
            for row in prices.itertuples(index=False)
        ]
        price_hash = sha(canonical_json(rows))
    manifest = {
        "engine_version": ENGINE_VERSION,
        "source_sha": source_sha,
        "sources": source_hashes,
        "prices": {
            "mode": "skipped" if skip_prices else "Sharadar SEP",
            "sha256": price_hash,
        },
    }
    return sha(canonical_json(manifest)), manifest


def sid(*parts: str) -> str:
    return sha("|".join(parts))[:40]


def f(v) -> float | None:
    """CSV cell → float or None. NaN/inf never enter the vector."""
    if v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


# =============================================================================
# Price fetch (Sharadar SEP, batched + paginated)
# =============================================================================

def fetch_prices(tickers: list[str], api_key: str) -> pd.DataFrame:
    """Daily closeadj for the last ~400 calendar days for all tickers."""
    since = (date.today() - timedelta(days=400)).isoformat()
    frames: list[pd.DataFrame] = []
    batch = 80
    for i in range(0, len(tickers), batch):
        chunk = tickers[i : i + batch]
        cursor = None
        while True:
            params = {
                "ticker": ",".join(chunk),
                "date.gte": since,
                "qopts.columns": "ticker,date,closeadj",
                "api_key": api_key,
            }
            if cursor:
                params["qopts.cursor_id"] = cursor
            r = requests.get(SEP_URL, params=params, timeout=120)
            r.raise_for_status()
            payload = r.json()["datatable"]
            frames.append(pd.DataFrame(payload["data"], columns=["ticker", "date", "closeadj"]))
            cursor = r.json().get("meta", {}).get("next_cursor_id")
            if not cursor:
                break
        print(f"  prices: {min(i + batch, len(tickers))}/{len(tickers)} tickers")
    px = pd.concat(frames, ignore_index=True)
    px["date"] = pd.to_datetime(px["date"]).dt.date
    return px.sort_values(["ticker", "date"])


def momentum_for(px: pd.DataFrame) -> dict[str, dict]:
    """Per ticker: last price/date, ret_1m/3m/12m, drawdown_from_peak."""
    out: dict[str, dict] = {}
    for t, g in px.groupby("ticker"):
        g = g.dropna(subset=["closeadj"])
        if len(g) < 22:
            continue
        closes = g["closeadj"].to_numpy()
        dates = g["date"].to_numpy()
        last, last_d = float(closes[-1]), dates[-1]

        def ret(days_back: int) -> float | None:
            target = last_d - timedelta(days=days_back)
            idx = None
            for j in range(len(dates) - 1, -1, -1):
                if dates[j] <= target:
                    idx = j
                    break
            if idx is None or closes[idx] <= 0:
                return None
            return last / float(closes[idx]) - 1.0

        peak = float(closes.max())
        out[t] = {
            "price": last,
            "price_date": last_d,
            "ret_1m": ret(30),
            "ret_3m": ret(91),
            "ret_12m": ret(365),
            "drawdown": last / peak - 1.0 if peak > 0 else None,
        }
    return out


# =============================================================================
# Build
# =============================================================================

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default=None)
    ap.add_argument("--skip-prices", action="store_true")
    ap.add_argument(
        "--activate",
        action="store_true",
        help="Deprecated: stage the data artifact and promote separately.",
    )
    args = ap.parse_args()
    if args.activate:
        raise SystemExit(
            "--activate is unsafe during a build. Stage the immutable data artifact "
            "first, then use scripts/activate_universe.py with its manifest hash."
        )
    build_source_sha = release_sha()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = date.today()

    panel = pd.read_csv(PANEL_CSV)
    overlay = pd.read_csv(OVERLAY_CSV).set_index("ticker")
    bundle = json.loads(BUNDLE_JSON.read_text())
    bundle_by_t = {c["ticker"]: c for c in bundle["companies"]}

    api_key = os.environ.get("NASDAQ_DATA_LINK_API_KEY")
    if not api_key:
        env_path = REPO / "deploy/.env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("NASDAQ_DATA_LINK_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
    tickers = sorted(panel["ticker"].dropna().unique().tolist())

    mom: dict[str, dict] = {}
    px: pd.DataFrame | None = None
    if not args.skip_prices:
        if not api_key:
            raise SystemExit("NASDAQ_DATA_LINK_API_KEY not found (env or deploy/.env)")
        print(f"Fetching prices for {len(tickers)} tickers …")
        px = fetch_prices(tickers, api_key)
        mom = momentum_for(px)
        print(f"  momentum computed for {len(mom)} tickers")

    input_sha256, manifest = build_manifest(
        prices=px,
        skip_prices=args.skip_prices,
        source_sha=build_source_sha,
    )
    universe_version = args.version or f"univ_{today.isoformat()}_{input_sha256[:12]}"
    manifest["universe_version"] = universe_version
    manifest["ticker_count"] = len(tickers)

    snapshots: list[dict] = []
    claims: list[dict] = []
    vectors: list[MetricVector] = []
    gate_rows: list[dict] = []

    # Cross-sectional inputs for offering_quality_z
    oq_components: dict[str, dict[str, float | None]] = {}

    panel_run_id = file_sha(PANEL_CSV)[:16]

    for _, row in panel.iterrows():
        t = str(row["ticker"])
        date_l = pd.to_datetime(row["date_l"]).date() if pd.notna(row.get("date_l")) else None
        ov = overlay.loc[t] if t in overlay.index else None
        bd = bundle_by_t.get(t)

        # ---- source snapshots -------------------------------------------------
        filing_date = None
        filing_asof = None
        accession = None
        if ov is not None and pd.notna(ov.get("filing_date")):
            filing_date = pd.to_datetime(ov["filing_date"]).date()
            accession = str(ov.get("accession")) if pd.notna(ov.get("accession")) else None
            # Fiscal period the filing covers (report_date); never after filing_date
            if pd.notna(ov.get("report_date")):
                filing_asof = pd.to_datetime(ov["report_date"]).date()
            if filing_asof is None or filing_asof > filing_date:
                filing_asof = filing_date

        # Panel values derive from Sharadar fundamentals, not the overlay filing:
        # the conservative reporting lag always applies (filing_date only dates
        # the overlay's own claims below).
        fund_asof = date_l or today
        fund_avail = fund_asof + timedelta(days=PANEL_PIT_LAG_DAYS)

        snap_panel = sid("panel", t, universe_version)
        snapshots.append(
            dict(
                snapshot_id=snap_panel,
                kind="sharadar_pull",
                ticker=t,
                as_of_date=fund_asof,
                available_date=fund_avail,
                fetched_at=now,
                locator=f"{PANEL_CSV.relative_to(REPO)}#run={panel_run_id}&ticker={t}",
                content_sha256=sha(row.to_json()),
                notes=f"Paper panel row; PIT lag {PANEL_PIT_LAG_DAYS}d conservative",
            )
        )

        snap_filing = None
        if accession:
            snap_filing = sid("10k", t, accession)
            filing_sha, filing_hash_note = filing_content_sha(t, accession, ov)
            snapshots.append(
                dict(
                    snapshot_id=snap_filing,
                    kind="10-K",
                    ticker=t,
                    as_of_date=filing_asof,
                    available_date=filing_date,
                    fetched_at=now,
                    locator=accession,
                    content_sha256=filing_sha,
                    notes=(
                        f"{filing_hash_note}; "
                        f"{ov.get('filing_url') if pd.notna(ov.get('filing_url')) else 'no URL'}"
                    ),
                )
            )

        snap_px = None
        m = mom.get(t)
        if m:
            snap_px = sid("sep", t, str(m["price_date"]))
            snapshots.append(
                dict(
                    snapshot_id=snap_px,
                    kind="sharadar_pull",
                    ticker=t,
                    as_of_date=m["price_date"],
                    available_date=m["price_date"],
                    fetched_at=now,
                    locator=f"SHARADAR/SEP?ticker={t}&date={m['price_date']}",
                    content_sha256=sha(f"{t}{m['price']}{m['price_date']}"),
                    notes="Daily adjusted close (momentum + live price)",
                )
            )

        # ---- claims + metric values ------------------------------------------
        def claim(field: str, value, text: str, snap: str, locator: str, unit=None, operator="=") -> str:
            cid = sid("c", t, field, universe_version)
            claims.append(
                dict(
                    claim_id=cid,
                    snapshot_id=snap,
                    ticker=t,
                    field=field,
                    value_text=text,
                    value_numeric=f(value),
                    operator=operator,
                    unit=unit,
                    excerpt_locator=locator,
                    extractor=ENGINE_VERSION,
                    extracted_at=now,
                )
            )
            return cid

        def mv_panel(field: str, col: str, formula: str, unit=None) -> MetricValue:
            v = f(row.get(col))
            if v is None:
                return MetricValue()
            cid = claim(field, v, str(row[col]), snap_panel, f"csv:{col}", unit)
            return MetricValue(
                value=v,
                as_of_date=fund_asof,
                available_date=fund_avail,
                claim_ids=[cid],
                formula=formula,
                engine_version=ENGINE_VERSION,
            )

        def mv_price(field: str, key: str, formula: str) -> MetricValue:
            if not m or m.get(key) is None:
                return MetricValue()
            v = float(m[key])
            cid = claim(field, v, f"{v:.6f}", snap_px, f"sep:{key}", None)
            return MetricValue(
                value=v,
                as_of_date=m["price_date"],
                available_date=m["price_date"],
                claim_ids=[cid],
                formula=formula,
                engine_version=ENGINE_VERSION,
            )

        # Retention / concentration / AI stance from 10-K overlay (verbatim only)
        retention = MetricValue()
        concentration = MetricValue()
        ai_stance = MetricValue()
        if ov is not None:
            if pd.notna(ov.get("nrr")) and snap_filing:
                op = str(ov.get("nrr_operator")) if pd.notna(ov.get("nrr_operator")) else "="
                op = op if op in ("=", ">", ">=", "<", "<=", "~") else "="
                cid = claim(
                    "retention", ov["nrr"],
                    str(ov.get("nrr_raw_match") or ov.get("nrr_raw") or ov["nrr"]),
                    snap_filing, "10-K NRR disclosure", "%", op,
                )
                retention = MetricValue(
                    value=f(ov["nrr"]), as_of_date=filing_asof, available_date=filing_date,
                    claim_ids=[cid], formula="disclosed NRR (verbatim)", engine_version=ENGINE_VERSION,
                )
            if pd.notna(ov.get("customer_concentration_top10")) and snap_filing:
                cid = claim(
                    "concentration", ov["customer_concentration_top10"],
                    str(ov.get("customer_concentration_raw_match") or ov["customer_concentration_top10"]),
                    snap_filing, "10-K concentration disclosure", "%",
                )
                concentration = MetricValue(
                    value=f(ov["customer_concentration_top10"]), as_of_date=filing_asof,
                    available_date=filing_date, claim_ids=[cid],
                    formula="disclosed top-10 customer concentration", engine_version=ENGINE_VERSION,
                )
            if pd.notna(ov.get("stance")):
                snap_for_stance = snap_filing or snap_panel
                cid = claim("ai_text_stance", ov["stance"], str(ov["stance"]), snap_for_stance,
                            "text_exposure signed stance")
                ai_stance = MetricValue(
                    value=f(ov["stance"]), as_of_date=filing_asof or fund_asof,
                    available_date=filing_date or fund_avail, claim_ids=[cid],
                    formula="signed augment-vs-automate stance (text_exposure.py)",
                    engine_version=ENGINE_VERSION,
                )

        # mos_live: fair band (snapshot) vs live price
        mos_live = MetricValue()
        fair_lo = f(row.get("fair_px_lo"))
        fair_med = f(row.get("fair_px_med"))
        fair_hi = f(row.get("fair_px_hi"))
        fair_band_valid = (
            fair_lo is not None
            and fair_med is not None
            and fair_hi is not None
            and 0 < fair_lo <= fair_med <= fair_hi
        )
        if m and fair_band_valid and fair_med and m["price"] > 0:
            v = fair_med / m["price"] - 1.0
            cid = claim("mos_live", v, f"fair_px_med {fair_med} / live {m['price']} - 1",
                        snap_px, "derived: fair_px_med(snapshot)/price(live)-1")
            mos_live = MetricValue(
                value=v, as_of_date=m["price_date"], available_date=m["price_date"],
                claim_ids=[cid],
                formula="mos_live = fair_px_med(as_of=date_l) / price(live) − 1 — DUAL AS-OF",
                engine_version=ENGINE_VERSION,
            )

        # Gates / kill / carve-out / table20 from bundle (where covered).
        # Unknown kill state is intentionally preserved for fail-closed ranking.
        table20 = None
        kill_active = KILL_ACTIVE.get(t)
        carve = None
        if bd:
            gates = bd.get("gates", {})
            base_gates = {k: v for k, v in gates.items() if not k.endswith("_live")}
            for gid, passed in base_gates.items():
                gate_rows.append(
                    dict(ticker=t, gate_id=gid, passed=bool(passed),
                         threshold="bundle gate (paper §8.1 family)",
                         observed=None, source_field=gid, claim_ids=[], evaluated_at=now)
                )
            # Strict Table-20 membership = paper tiers only; count 12 for members,
            # else the number of passing bundle gates (honest partial, max < 12).
            if bd.get("paper_tier") in ("tier1", "tier2"):
                table20 = 12
            else:
                table20 = min(sum(1 for v in base_gates.values() if v), 11)
            if t in KILL_ACTIVE:
                kill_active = KILL_ACTIVE[t]
            carve = not gates.get("g1_saas_universe", True)

        route = "carved_out" if carve else (
            str(row["vgroup"]) if row.get("vgroup") in ("fcf_positive", "pre_fcf") else None
        )
        if fair_band_valid:
            fair_lo_mv = mv_panel(
                "fair_px_lo", "fair_px_lo", "triangulated conservative fair-value lens", "USD/share"
            )
            fair_med_mv = mv_panel(
                "fair_px_med", "fair_px_med", "triangulated median fair-value lens", "USD/share"
            )
            fair_hi_mv = mv_panel(
                "fair_px_hi", "fair_px_hi", "triangulated upper fair-value lens", "USD/share"
            )
        else:
            fair_lo_mv = fair_med_mv = fair_hi_mv = MetricValue()

        vec = MetricVector(
            ticker=t,
            universe_version=universe_version,
            computed_at=now,
            product_map_complete=bool(bd) or None,
            competitor_set_n=None,
            retention=retention,
            concentration=concentration,
            moat_direction=None,
            offering_quality_z=MetricValue(),  # filled cross-sectionally below
            fair_px_lo=fair_lo_mv,
            fair_px_med=fair_med_mv,
            fair_px_hi=fair_hi_mv,
            mos_snapshot=mv_panel("mos_snapshot", "mos", "triangulated fair band vs price (valuation_engine)"),
            mos_live=mos_live,
            table20_pass_count=table20,
            kill_active=kill_active,
            cohort=str(bd["cohort"]) if bd and bd.get("cohort") else (str(row["cohort"]) if pd.notna(row.get("cohort")) else None),
            rd_int=mv_panel("rd_int", "rd_int_l", "R&D / revenue (rd_alpha.py)"),
            rd_gp=mv_panel("rd_gp", "rd_gp_l", "R&D / gross profit"),
            rd_mom=mv_panel("rd_mom", "rd_mom", "R&D momentum"),
            rd_capital=mv_panel("rd_capital", "rd_capital", "Lev-Sougiannis capitalized R&D, δ=0.20"),
            rd_prod=mv_panel("rd_prod", "rd_prod", "R&D productivity"),
            rd_cap_to_ev=mv_panel("rd_cap_to_ev", "rd_cap_to_ev", "capitalized R&D / EV"),
            gm=mv_panel("gm", "gm_l", "gross margin (latest)"),
            fcfm_sbc=mv_panel("fcfm_sbc", "fcfm_sbc_l", "FCF margin, SBC-adjusted (owner earnings)"),
            roic=mv_panel("roic", "roic_l", "return on invested capital"),
            rule40=mv_panel("rule40", "rule40_sbc_l", "revenue growth + SBC-adj FCF margin"),
            sbc_intensity=mv_panel("sbc_intensity", "sbc_pct_l", "SBC / revenue"),
            rev_cagr=mv_panel("rev_cagr", "rev_cagr", "revenue CAGR over span"),
            dilution_ann=mv_panel("dilution_ann", "dilution_ann", "annualized share dilution"),
            runway_yrs=mv_panel("runway_yrs", "runway_yrs", "net cash / burn (pre-FCF route)"),
            ret_1m=mv_price("ret_1m", "ret_1m", "closeadj[t]/closeadj[t−30d] − 1"),
            ret_3m=mv_price("ret_3m", "ret_3m", "closeadj[t]/closeadj[t−91d] − 1"),
            ret_12m=mv_price("ret_12m", "ret_12m", "closeadj[t]/closeadj[t−365d] − 1"),
            drawdown_from_peak=mv_price("drawdown_from_peak", "drawdown", "price/rolling-peak − 1"),
            ai_text_stance=ai_stance,
            float_fcf_share=MetricValue(),  # not yet extracted — stays Unknown
            carve_out=carve,
            route=route,
            completeness=ResearchCompleteness(  # provisional; finalized below
                grade="Incomplete", filing_fetched=snap_filing is not None,
                claims_n=0, dcf_reproducible=False, overlay_fill_rate=0.0,
                competitor_map_filled=False,
                asof_freshness_days=(today - fund_asof).days if fund_asof else None,
                stale=bool(fund_asof and (today - fund_asof).days > STALE_SLA_DAYS),
            ),
        )
        vectors.append(vec)

        oq_components[t] = {
            "retention": retention.value,
            "gm": vec.gm.value,
            "rd_prod": vec.rd_prod.value,
            "rule40": vec.rule40.value,
            "concentration": concentration.value,
        }

    # ---- offering_quality_z (cross-sectional robust z; ≥3 known components) ----
    comp_names = ["retention", "gm", "rd_prod", "rule40", "concentration"]
    zs = {
        c: robust_z([oq_components[v.ticker][c] for v in vectors])
        for c in comp_names
    }
    for i, v in enumerate(vectors):
        parts = []
        for c in comp_names:
            z = zs[c][i]
            if z is not None:
                parts.append(-z if c == "concentration" else z)
        if len(parts) >= 3:
            asof = v.gm.as_of_date or today
            avail = v.gm.available_date or today
            v.offering_quality_z = MetricValue(
                value=round(sum(parts), 6), as_of_date=asof, available_date=avail,
                claim_ids=[],
                formula="Σ z(retention, gm, rd_prod, rule40, −concentration); ≥3 known components; MAD z winsor ±3",
                engine_version=ENGINE_VERSION,
            )

    # ---- completeness grading --------------------------------------------------
    for v in vectors:
        t = v.ticker
        n_claims = sum(1 for c in claims if c["ticker"] == t)
        core = [v.mos_snapshot, v.gm, v.fcfm_sbc, v.roic, v.rule40, v.rd_prod, v.rd_int]
        overlay_fields = [v.retention, v.concentration, v.ai_text_stance]
        fill = sum(1 for x in overlay_fields if x.value is not None) / len(overlay_fields)
        core_ok = sum(1 for x in core if x.value is not None)
        filing = v.completeness.filing_fetched
        if filing and core_ok == len(core) and fill >= 2 / 3:
            grade = "A"
        elif filing and core_ok >= 5:
            grade = "B"
        elif core_ok >= 5:
            grade = "C"
        else:
            grade = "Incomplete"
        v.completeness = ResearchCompleteness(
            grade=grade,
            filing_fetched=filing,
            claims_n=n_claims,
            dcf_reproducible=v.mos_snapshot.value is not None,
            overlay_fill_rate=round(fill, 4),
            competitor_map_filled=False,
            asof_freshness_days=v.completeness.asof_freshness_days,
            stale=v.completeness.stale,
        )

    # ---- write to Postgres -------------------------------------------------------
    import asyncio
    import asyncpg

    dsn = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/rd_alpha")
    dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    async def write() -> bool:
        conn = await asyncpg.connect(dsn)
        try:
            async with conn.transaction():
                builds_table = await conn.fetchval(
                    "SELECT to_regclass('public.universe_builds')"
                )
                if builds_table is None:
                    raise RuntimeError(
                        "universe_builds is missing; apply migration "
                        "011_release_integrity.sql before building."
                    )
                existing = await conn.fetchrow(
                    "SELECT input_sha256 FROM universe_builds WHERE universe_version=$1",
                    universe_version,
                )
                if existing:
                    if existing["input_sha256"] == input_sha256:
                        print(
                            f"Universe {universe_version} is already sealed with "
                            "the same input manifest; no mutation performed."
                        )
                        return False
                    raise RuntimeError(
                        f"Universe version {universe_version} is already sealed "
                        "with different inputs; choose a new version."
                    )
                prior_version = await conn.fetchval(
                    "SELECT universe_version FROM universe_builds WHERE input_sha256=$1",
                    input_sha256,
                )
                if prior_version:
                    raise RuntimeError(
                        f"These exact inputs are already sealed as {prior_version}; "
                        "do not duplicate an immutable build."
                    )
                legacy_vectors = await conn.fetchval(
                    "SELECT count(*) FROM metric_vectors WHERE universe_version=$1",
                    universe_version,
                )
                if legacy_vectors:
                    raise RuntimeError(
                        f"Universe version {universe_version} already has "
                        f"{legacy_vectors} vectors but no build manifest; refusing "
                        "to overwrite legacy research."
                    )
                await conn.execute(
                    """INSERT INTO universe_builds
                       (universe_version, input_sha256, manifest, engine_version, status, sealed_at, is_active, source_sha)
                       VALUES ($1,$2,$3::jsonb,$4,'building',NULL,false,$5)""",
                    universe_version,
                    input_sha256,
                    json.dumps(manifest),
                    ENGINE_VERSION,
                    build_source_sha,
                )
                await conn.executemany(
                    """INSERT INTO source_snapshots
                       (snapshot_id, kind, ticker, as_of_date, available_date, fetched_at, locator, content_sha256, notes)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                       ON CONFLICT (snapshot_id) DO NOTHING""",
                    [(s["snapshot_id"], s["kind"], s["ticker"], s["as_of_date"], s["available_date"],
                      s["fetched_at"], s["locator"], s["content_sha256"], s["notes"]) for s in snapshots],
                )
                await conn.executemany(
                    """INSERT INTO evidence_claims
                       (claim_id, snapshot_id, ticker, field, value_text, value_numeric, operator, unit, excerpt_locator, extractor, extracted_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                       ON CONFLICT (claim_id) DO NOTHING""",
                    [(c["claim_id"], c["snapshot_id"], c["ticker"], c["field"], c["value_text"],
                      c["value_numeric"], c["operator"], c["unit"], c["excerpt_locator"],
                      c["extractor"], c["extracted_at"]) for c in claims],
                )
                await conn.executemany(
                    """INSERT INTO metric_vectors
                       (ticker, universe_version, computed_at, vector, completeness_grade, route, kill_active, stale)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                       ON CONFLICT (ticker, universe_version) DO NOTHING""",
                    [(v.ticker, v.universe_version, v.computed_at,
                      json.dumps(v.model_dump(mode="json")), v.completeness.grade,
                      v.route, v.kill_active, v.completeness.stale) for v in vectors],
                )
                await conn.executemany(
                    """INSERT INTO gate_evaluations
                       (ticker, gate_id, passed, threshold, observed, source_field, claim_ids, evaluated_at, universe_version)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
                    [(g["ticker"], g["gate_id"], g["passed"], g["threshold"], g["observed"],
                      g["source_field"], json.dumps(g["claim_ids"]), g["evaluated_at"], universe_version)
                     for g in gate_rows],
                )
                await conn.executemany(
                    """INSERT INTO literature_binds (axis, bib_key, citation, paper_section, url_or_doi)
                       VALUES ($1,$2,$3,$4,$5) ON CONFLICT (axis, bib_key) DO NOTHING""",
                    [(b.axis, b.bib_key, b.citation, b.paper_section, b.url_or_doi) for b in LITERATURE_BINDS],
                )
                await conn.executemany(
                    """INSERT INTO rank_recipes (recipe_key, recipe_id, name, formula_human, formula_exact, hard_filters, axes, benchmark_vs, custom)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
                       ON CONFLICT (recipe_key) DO UPDATE SET
                         formula_human = EXCLUDED.formula_human, formula_exact = EXCLUDED.formula_exact,
                         hard_filters = EXCLUDED.hard_filters, axes = EXCLUDED.axes""",
                    [(r.recipe_id, r.recipe_id, r.name, r.formula_human, r.formula_exact,
                      json.dumps(r.hard_filters), json.dumps(r.axes), r.benchmark_vs, False)
                     for r in PRESET_RECIPES],
                )
                await conn.fetchval(
                    "SELECT materialize_universe_evidence_refs($1)",
                    universe_version,
                )
                if args.activate:
                    await conn.execute("SELECT pg_advisory_xact_lock(842183002)")
                    await conn.execute(
                        "UPDATE universe_builds SET is_active=false WHERE is_active"
                    )
                await conn.execute(
                    """UPDATE universe_builds
                       SET status='sealed', sealed_at=CURRENT_TIMESTAMP, is_active=$2
                       WHERE universe_version=$1 AND status='building'""",
                    universe_version,
                    args.activate,
                )
                return True
        finally:
            await conn.close()

    written = asyncio.run(write())
    if not written:
        return

    manifest_dir = REPO / "data" / "universe_manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{universe_version}.json"
    manifest_path.write_text(
        json.dumps(
            {
                **manifest,
                "input_sha256": input_sha256,
                "created_at": now.isoformat(),
            },
            indent=2,
            sort_keys=True,
        )
    )

    grades = {}
    for v in vectors:
        grades[v.completeness.grade] = grades.get(v.completeness.grade, 0) + 1
    print(f"\nUniverse build {universe_version}:")
    print(f"  input_sha256: {input_sha256}")
    print(f"  activated: {args.activate}")
    print(f"  vectors: {len(vectors)}  snapshots: {len(snapshots)}  claims: {len(claims)}  gates: {len(gate_rows)}")
    print(f"  grades: {grades}")
    print(f"  routes: fcf+={sum(1 for v in vectors if v.route == 'fcf_positive')} "
          f"pre_fcf={sum(1 for v in vectors if v.route == 'pre_fcf')} "
          f"carved={sum(1 for v in vectors if v.route == 'carved_out')}")
    print(f"  momentum coverage: {sum(1 for v in vectors if v.ret_12m.value is not None)}")
    print(f"  mos_live coverage: {sum(1 for v in vectors if v.mos_live.value is not None)}")


if __name__ == "__main__":
    main()
