"""
PATH: research/paper_latex/scripts/build_assets.py
PURPOSE:
  Generate LaTeX-ready, submission-grade assets (tables, plot CSVs, and numeric macros)
  from the frozen `publication_snapshot.json` used by the live website.

WHY:
  - A submission PDF must be reproducible and stable for printing.
  - Manual copy/paste of numbers causes drift and inconsistencies across versions.
  - This script ensures every numeric claim in the LaTeX paper is pinned to a snapshot.

FLOW:
  ┌──────────────────────────┐
  │ Read publication snapshot │
  └──────────────┬───────────┘
                 ▼
  ┌──────────────────────────┐
  │ Write numeric macros (.tex)│  → data/metrics.tex
  ├──────────────────────────┤
  │ Write CSVs for pgfplots   │  → data/*.csv
  ├──────────────────────────┤
  │ Write TeX tables          │  → tables/*.tex
  └──────────────────────────┘

DEPENDENCIES:
  - data/publication_snapshot.json
  - Python stdlib only (json, csv, pathlib, datetime, typing)
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
TABLES_DIR = BASE_DIR / "tables"

SNAPSHOT_PATH = DATA_DIR / "publication_snapshot.json"


def _latex_escape_text(value: str) -> str:
    """
    Escape LaTeX special characters in plain text.

    WHY:
      Snapshot metadata (e.g., `july_june`) can contain characters like `_` that
      would otherwise break LaTeX compilation.
    """
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    out = []
    for ch in value:
        out.append(replacements.get(ch, ch))
    return "".join(out)


def _format_return_convention(value: str | None) -> str:
    """
    Convert internal labels to manuscript-friendly LaTeX-safe text.
    """
    if not value:
        return "--"
    if value == "july_june":
        return "July--June"
    if value == "calendar":
        return "Calendar year"
    return _latex_escape_text(value)


def _safe_float(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _safe_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    return None


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    # Remove previously generated tables to avoid “stale table” artifacts when the new snapshot
    # omits an optional section. We regenerate (or placeholder-generate) all `table_*.tex` files.
    for p in TABLES_DIR.glob("table_*.tex"):
        try:
            p.unlink()
        except Exception:
            # Best-effort; if deletion fails, subsequent writes will still overwrite in most cases.
            pass


def _read_snapshot() -> tuple[dict[str, Any], dict[str, Any]]:
    raw = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    meta = raw.get("meta") or {}
    payload = raw.get("payload") or {}
    if not isinstance(meta, dict) or not isinstance(payload, dict):
        raise ValueError("Snapshot JSON invalid: expected top-level {meta, payload} objects.")
    return meta, payload


def _fmt_pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "--"
    return f"{value:.{decimals}f}"


def _fmt_p_value(value: float | None) -> str:
    if value is None:
        return "--"
    if value < 0.001:
        return "<0.001"
    return f"{value:.4f}"


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def write_metrics_tex(meta: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    Writes `data/metrics.tex` containing numeric macros used by `main.tex`.
    """
    annual = payload.get("annual_hml_premium") if isinstance(payload.get("annual_hml_premium"), dict) else {}
    hac = annual.get("hac_adjusted") if isinstance(annual.get("hac_adjusted"), dict) else {}
    tx = payload.get("transaction_costs") if isinstance(payload.get("transaction_costs"), dict) else {}
    stats = payload.get("publication_stats") if isinstance(payload.get("publication_stats"), dict) else {}
    annual_rows = annual.get("annual_premiums") if isinstance(annual.get("annual_premiums"), list) else []

    mean_premium = _safe_float(annual.get("mean_premium"))
    t_stat = _safe_float(hac.get("t_statistic"))
    p_val = _safe_float(hac.get("p_value"))
    n_years = _safe_int(annual.get("n_years"))
    positive_years = _safe_int(annual.get("positive_years"))
    win_rate = _safe_float(annual.get("win_rate"))

    trading_cost_pct = _safe_float(tx.get("annual_trading_cost_pct"))
    net_premium_pct = _safe_float(tx.get("net_rd_premium_pct"))
    gross_premium_pct = _safe_float(tx.get("gross_rd_premium_pct"))
    capture_rate_pct = _safe_float(tx.get("premium_capture_rate_pct"))

    # Backtest period labels (from transaction_costs, for LaTeX macros)
    backtest_start_year = _safe_int(tx.get("backtest_start_year"))
    backtest_end_year = _safe_int(tx.get("backtest_end_year"))
    backtest_n_periods = _safe_int(tx.get("n_periods"))
    backtest_period_label_raw = tx.get("period_label") if isinstance(tx.get("period_label"), str) else None
    backtest_period_label = _latex_escape_text(backtest_period_label_raw).replace("-", "--") if backtest_period_label_raw else "--"

    built_at = meta.get("built_at")
    built_at_label = None
    if isinstance(built_at, str) and built_at:
        try:
            built_at_label = datetime.fromisoformat(built_at.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            built_at_label = built_at

    return_convention_raw = meta.get("return_convention") if isinstance(meta.get("return_convention"), str) else None
    return_convention = _format_return_convention(return_convention_raw)

    data_tier_raw = meta.get("data_tier") if isinstance(meta.get("data_tier"), str) else None
    data_tier = _latex_escape_text(data_tier_raw) if data_tier_raw else "--"

    win_rate_pct = (win_rate * 100.0) if isinstance(win_rate, float) else None

    # --- Derived summary stats (computed from snapshot objects; used to avoid hard-coding prose numbers) ---
    # Mean Q1/Q5 returns for the annual non-overlapping series
    q1_vals: list[float] = []
    q5_vals: list[float] = []
    for r in annual_rows:
        if not isinstance(r, dict):
            continue
        q1 = _safe_float(r.get("q1_return"))
        q5 = _safe_float(r.get("q5_return"))
        if q1 is None or q5 is None:
            continue
        q1_vals.append(q1)
        q5_vals.append(q5)
    annual_mean_q1 = (sum(q1_vals) / len(q1_vals)) if q1_vals else None
    annual_mean_q5 = (sum(q5_vals) / len(q5_vals)) if q5_vals else None

    # Rolling-window HML premiums (descriptive; overlapping windows)
    def _rolling_hml_premium(h: str) -> float | None:
        node = stats.get(h)
        if not isinstance(node, dict):
            return None
        means = node.get("quintile_means") if isinstance(node.get("quintile_means"), dict) else {}
        q1 = _safe_float(means.get("Q1"))
        q5 = _safe_float(means.get("Q5"))
        if q1 is None or q5 is None:
            return None
        return q5 - q1

    rolling_5yr_premium = _rolling_hml_premium("5yr")
    rolling_10yr_premium = _rolling_hml_premium("10yr")
    rolling_20yr_premium = _rolling_hml_premium("20yr")

    # Annual series label range for manuscript prose (e.g., Jul2001--Jun2002)
    def _annual_label_row(x: Any) -> tuple[int, str] | None:
        if not isinstance(x, dict):
            return None
        formation_year = _safe_int(x.get("formation_year"))
        label = x.get("year") if isinstance(x.get("year"), str) else None
        if formation_year is None or not label:
            return None
        return (formation_year, label)

    labels = [_annual_label_row(r) for r in annual_rows]
    labels = [x for x in labels if x is not None]
    labels.sort(key=lambda t: t[0])
    annual_period_start = labels[0][1].replace("-", "--") if labels else "--"
    annual_period_end = labels[-1][1].replace("-", "--") if labels else "--"

    snapshot_id_raw = meta.get("id") if isinstance(meta.get("id"), str) else None
    snapshot_id = _latex_escape_text(snapshot_id_raw) if snapshot_id_raw else None

    content = "\n".join(
        [
            "% Auto-generated. Do not edit by hand.",
            "% Regenerate via: python3 scripts/build_assets.py",
            "",
            f"\\newcommand{{\\SnapshotId}}{{{snapshot_id or '--'}}}",
            f"\\newcommand{{\\SnapshotBuiltAt}}{{{built_at_label or '--'}}}",
            f"\\newcommand{{\\ReturnConvention}}{{{return_convention or '--'}}}",
            f"\\newcommand{{\\DataTier}}{{{data_tier or '--'}}}",
            f"\\newcommand{{\\AnnualSeriesStart}}{{{annual_period_start}}}",
            f"\\newcommand{{\\AnnualSeriesEnd}}{{{annual_period_end}}}",
            "",
            f"\\newcommand{{\\AnnualMeanPremium}}{{{_fmt_pct(mean_premium, 2)}}}",
            f"\\newcommand{{\\AnnualTStat}}{{{_fmt_pct(t_stat, 2)}}}",
            f"\\newcommand{{\\AnnualPValue}}{{{_fmt_p_value(p_val)}}}",
            f"\\newcommand{{\\AnnualNYears}}{{{n_years or 0}}}",
            f"\\newcommand{{\\AnnualPositiveYears}}{{{positive_years or 0}}}",
            f"\\newcommand{{\\AnnualWinRatePct}}{{{_fmt_pct(win_rate_pct, 0)}}}",
            # NOTE: LaTeX control sequence names cannot contain digits. Use words instead of Q1/Q5.
            f"\\newcommand{{\\AnnualMeanQOneReturn}}{{{_fmt_pct(annual_mean_q1, 2)}}}",
            f"\\newcommand{{\\AnnualMeanQFiveReturn}}{{{_fmt_pct(annual_mean_q5, 2)}}}",
            "",
            f"\\newcommand{{\\RollingFiveYearPremium}}{{{_fmt_pct(rolling_5yr_premium, 2)}}}",
            f"\\newcommand{{\\RollingTenYearPremium}}{{{_fmt_pct(rolling_10yr_premium, 2)}}}",
            f"\\newcommand{{\\RollingTwentyYearPremium}}{{{_fmt_pct(rolling_20yr_premium, 2)}}}",
            "",
            f"\\newcommand{{\\AnnualTradingCostPct}}{{{_fmt_pct(trading_cost_pct, 3)}}}",
            f"\\newcommand{{\\GrossPremiumAfterFormationPct}}{{{_fmt_pct(gross_premium_pct, 2)}}}",
            f"\\newcommand{{\\NetPremiumAfterCostsPct}}{{{_fmt_pct(net_premium_pct, 2)}}}",
            f"\\newcommand{{\\PremiumCaptureRatePct}}{{{_fmt_pct(capture_rate_pct, 1)}}}",
            "",
            "% Investable backtest period macros (RD20 strategy vs SPY)",
            f"\\newcommand{{\\BacktestStartYear}}{{{backtest_start_year or 2001}}}",
            f"\\newcommand{{\\BacktestEndYear}}{{{backtest_end_year or 2024}}}",
            f"\\newcommand{{\\BacktestNYears}}{{{backtest_n_periods or 24}}}",
            f"\\newcommand{{\\BacktestPeriodLabel}}{{{backtest_period_label}}}",
            "",
        ]
    )

    (DATA_DIR / "metrics.tex").write_text(content + "\n", encoding="utf-8")


def write_rd_trends_csv(payload: dict[str, Any]) -> None:
    rows = payload.get("rd_trends")
    if not isinstance(rows, list):
        rows = []

    out_rows: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        year = _safe_int(r.get("year"))
        avg = _safe_float(r.get("avg_rd_intensity"))
        companies = _safe_int(r.get("companies"))
        if year is None or avg is None:
            continue
        out_rows.append(
            {
                "year": year,
                "avg_rd_intensity": avg,
                "companies": companies if companies is not None else "",
            }
        )

    _write_csv(DATA_DIR / "rd_trends.csv", ["year", "avg_rd_intensity", "companies"], out_rows)


def write_annual_hml_csv(payload: dict[str, Any]) -> None:
    annual = payload.get("annual_hml_premium")
    if not isinstance(annual, dict):
        return
    rows = annual.get("annual_premiums")
    if not isinstance(rows, list):
        return

    out_rows: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        formation_year = _safe_int(r.get("formation_year"))
        premium = _safe_float(r.get("hml_premium"))
        q1 = _safe_float(r.get("q1_return"))
        q5 = _safe_float(r.get("q5_return"))
        label = r.get("year") if isinstance(r.get("year"), str) else ""
        if formation_year is None or premium is None:
            continue

        # Plot x-axis by return-period start year = formation_year + 1 (July of T+1).
        year_start = formation_year + 1
        out_rows.append(
            {
                "year_start": year_start,
                "return_period": label,
                "q5_return": q5 if q5 is not None else "",
                "q1_return": q1 if q1 is not None else "",
                "hml_premium": premium,
            }
        )

    out_rows.sort(key=lambda x: x["year_start"])
    _write_csv(
        DATA_DIR / "annual_hml_premium.csv",
        ["year_start", "return_period", "q5_return", "q1_return", "hml_premium"],
        out_rows,
    )


def write_annual_quintile_growth_csv(payload: dict[str, Any]) -> None:
    """
    Convenience series for a simple "growth of $1" chart using the annual non-overlapping series.

    WHY:
      The website renders this interactively; the LaTeX paper needs a deterministic, print-ready figure.
      We compute cumulative wealth indices for Q5 and Q1 using the same annual return series used for
      primary inference (July--June non-overlapping observations).
    """
    annual = payload.get("annual_hml_premium")
    if not isinstance(annual, dict):
        return
    rows = annual.get("annual_premiums")
    if not isinstance(rows, list):
        return

    # Sort by formation year to maintain chronological order.
    parsed: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        fy = _safe_int(r.get("formation_year"))
        q1 = _safe_float(r.get("q1_return"))
        q5 = _safe_float(r.get("q5_return"))
        if fy is None or q1 is None or q5 is None:
            continue
        parsed.append({"formation_year": fy, "q1_return": q1, "q5_return": q5})

    parsed.sort(key=lambda x: x["formation_year"])

    q1_index = 1.0
    q5_index = 1.0
    out_rows: list[dict[str, Any]] = []
    for r in parsed:
        year_start = int(r["formation_year"]) + 1
        q1_index *= 1.0 + float(r["q1_return"]) / 100.0
        q5_index *= 1.0 + float(r["q5_return"]) / 100.0
        out_rows.append({"year_start": year_start, "q5_index": q5_index, "q1_index": q1_index})

    _write_csv(DATA_DIR / "annual_quintile_growth.csv", ["year_start", "q5_index", "q1_index"], out_rows)


def write_factor_premiums_csv(payload: dict[str, Any]) -> None:
    """
    Convenience series used by the website to compute the long-run sample range and growth charts.
    """
    rows = payload.get("factor_premiums")
    if not isinstance(rows, list):
        return

    out_rows: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        year = _safe_int(r.get("year"))
        if year is None:
            continue
        out_rows.append(
            {
                "year": year,
                "q1_return": _safe_float(r.get("q1_return")) or "",
                "q5_return": _safe_float(r.get("q5_return")) or "",
                "rd_premium": _safe_float(r.get("rd_premium")) or "",
            }
        )

    out_rows.sort(key=lambda x: x["year"])
    _write_csv(DATA_DIR / "factor_premiums.csv", ["year", "q1_return", "q5_return", "rd_premium"], out_rows)


def write_quintile_means_csv(payload: dict[str, Any]) -> None:
    stats = payload.get("publication_stats")
    if not isinstance(stats, dict):
        return

    for horizon in ("5yr", "10yr", "20yr"):
        node = stats.get(horizon)
        if not isinstance(node, dict):
            continue
        means = node.get("quintile_means")
        if not isinstance(means, dict):
            continue

        out_rows: list[dict[str, Any]] = []
        for q in ("Q1", "Q2", "Q3", "Q4", "Q5"):
            v = _safe_float(means.get(q))
            if v is None:
                continue
            out_rows.append({"quintile": q, "avg_return": v})

        _write_csv(DATA_DIR / f"quintile_means_{horizon}.csv", ["quintile", "avg_return"], out_rows)


def write_investable_growth_csv(payload: dict[str, Any]) -> None:
    bt = payload.get("investable_backtest")
    if not isinstance(bt, dict):
        return
    rows = bt.get("yearly_data")
    if not isinstance(rows, list):
        return

    # Compute cumulative indices, excluding incomplete years (where sp500_return is None).
    portfolio = 1.0
    benchmark = 1.0
    sp500 = 1.0

    out_rows: list[dict[str, Any]] = []
    for r in sorted((x for x in rows if isinstance(x, dict)), key=lambda x: x.get("year", 0)):
        year = _safe_int(r.get("year"))
        if year is None:
            continue

        sp_ret = _safe_float(r.get("sp500_return"))
        if sp_ret is None:
            # incomplete; stop the series
            break

        port_ret = _safe_float(r.get("portfolio_return_net")) or _safe_float(r.get("portfolio_return")) or 0.0
        bench_ret = _safe_float(r.get("benchmark_return_net")) or _safe_float(r.get("benchmark_return")) or 0.0

        portfolio *= 1.0 + port_ret / 100.0
        benchmark *= 1.0 + bench_ret / 100.0
        sp500 *= 1.0 + sp_ret / 100.0

        out_rows.append(
            {
                "year": year,
                "portfolio_index": portfolio,
                "benchmark_index": benchmark,
                "sp500_index": sp500,
            }
        )

    _write_csv(DATA_DIR / "investable_growth.csv", ["year", "portfolio_index", "benchmark_index", "sp500_index"], out_rows)


def write_tables(meta: dict[str, Any], payload: dict[str, Any]) -> None:
    """
    Writes TeX tables under `tables/` using booktabs.
    """
    cohort = payload.get("cohort_summary") if isinstance(payload.get("cohort_summary"), dict) else {}
    annual = payload.get("annual_hml_premium") if isinstance(payload.get("annual_hml_premium"), dict) else {}
    hac = annual.get("hac_adjusted") if isinstance(annual.get("hac_adjusted"), dict) else {}
    stats = payload.get("publication_stats") if isinstance(payload.get("publication_stats"), dict) else {}
    tx = payload.get("transaction_costs") if isinstance(payload.get("transaction_costs"), dict) else {}
    methodology = payload.get("methodology_parameters") if isinstance(payload.get("methodology_parameters"), dict) else {}
    rd_by_sector = payload.get("rd_by_sector") if isinstance(payload.get("rd_by_sector"), list) else []

    total_companies = _safe_int(cohort.get("total_companies"))
    eligible_5yr = _safe_int(cohort.get("eligible_5yr"))
    eligible_10yr = _safe_int(cohort.get("eligible_10yr"))
    eligible_20yr = _safe_int(cohort.get("eligible_20yr"))
    avg_rd_intensity = _safe_float(cohort.get("avg_rd_intensity"))
    avg_quality_score = _safe_float(cohort.get("avg_quality_score"))

    # Use a short, paper-friendly build date label (avoid long ISO timestamps in table captions).
    built_at_raw = meta.get("built_at")
    built_at_label = "--"
    if isinstance(built_at_raw, str) and built_at_raw:
        try:
            built_at_label = datetime.fromisoformat(built_at_raw.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            built_at_label = built_at_raw
    built_at = _latex_escape_text(built_at_label)
    return_convention = _format_return_convention(meta.get("return_convention") if isinstance(meta.get("return_convention"), str) else None)
    data_tier_raw = meta.get("data_tier") if isinstance(meta.get("data_tier"), str) else None
    data_tier = _latex_escape_text(data_tier_raw) if data_tier_raw else "--"

    table_sample = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Sample construction and data tier (snapshot built: {built_at})}}
\\label{{tab:sample}}
\\begin{{tabular}}{{p{{0.41\\textwidth}}p{{0.52\\textwidth}}}}
\\toprule
Item & Value \\\\
\\midrule
Universe & Current S\\&P 500 (add-date gated; Tier-1) \\\\
Return convention & {return_convention} \\\\
Data tier & {data_tier} \\\\
Unique tickers in cohort$^{{*}}$ & {total_companies or '--'} \\\\
Eligible with 5-year window coverage & {eligible_5yr or '--'} \\\\
Eligible with 10-year window coverage & {eligible_10yr or '--'} \\\\
Eligible with 20-year window coverage & {eligible_20yr or '--'} \\\\
Average R\\&D intensity (\\%) & {_fmt_pct(avg_rd_intensity,2)} \\\\
Average data quality score (0--100) & {_fmt_pct(avg_quality_score,1)} \\\\
\\bottomrule
\\end{{tabular}}
\\\\[2pt]
\\footnotesize{{$^{{*}}$Union of companies with data in the snapshot. In Tier-1, index eligibility is enforced using addition dates for the current S\\&P 500 list; historical removals and historical constituents not in the current list are not tracked (see Table~\\ref{{tab:universe_integrity}}).}}
\\end{{table}}
"""

    (TABLES_DIR / "table_sample.tex").write_text(table_sample, encoding="utf-8")

    # Methodology parameter table (snapshot-pinned)
    filters = methodology.get("filters") if isinstance(methodology.get("filters"), dict) else {}
    capping = filters.get("rd_intensity_capping") if isinstance(filters.get("rd_intensity_capping"), dict) else {}
    portfolio = methodology.get("portfolio_construction") if isinstance(methodology.get("portfolio_construction"), dict) else {}
    sanity = methodology.get("sanity_check_constants") if isinstance(methodology.get("sanity_check_constants"), dict) else {}

    min_rev = _safe_float(filters.get("min_revenue_threshold_usd"))
    min_rev_label = f"\\${min_rev/1e6:.0f}M" if isinstance(min_rev, float) else "--"
    default_cap = _safe_float(capping.get("default_cap_pct"))
    high_cap = _safe_float(capping.get("high_rd_sector_cap_pct"))
    n_quintiles = _safe_int(portfolio.get("n_quintiles"))
    weighting = portfolio.get("weighting") if isinstance(portfolio.get("weighting"), str) else "--"
    rebal = portfolio.get("rebalance_frequency") if isinstance(portfolio.get("rebalance_frequency"), str) else "--"

    win_lo = _safe_int(sanity.get("winsorize_lower_pct"))
    win_hi = _safe_int(sanity.get("winsorize_upper_pct"))

    table_method = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Portfolio formation and data filters (snapshot parameters)}}
\\label{{tab:methodology_params}}
\\begin{{tabular}}{{ll}}
\\toprule
Parameter & Value \\\\
\\midrule
Universe & { _latex_escape_text(str(methodology.get('universe','--'))) if methodology.get('universe') else '--' } \\\\
Return convention & { _format_return_convention(methodology.get('return_convention') if isinstance(methodology.get('return_convention'), str) else None) } \\\\
Rebalance frequency & { _latex_escape_text(rebal) } \\\\
Quintiles & {n_quintiles or '--'} \\\\
Weighting & { _latex_escape_text(weighting) } \\\\
Min revenue threshold & {min_rev_label} \\\\
R\\&D intensity cap (default) & {_fmt_pct(default_cap,0)}\\% \\\\
R\\&D intensity cap (high-R\\&D sectors) & {_fmt_pct(high_cap,0)}\\% \\\\
Winsorization (annual returns) & {win_lo if win_lo is not None else '--'}--{win_hi if win_hi is not None else '--'} percentile \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_methodology_params.tex").write_text(table_method, encoding="utf-8")

    # Sector R&D intensity table (top sectors)
    sector_rows: list[dict[str, Any]] = []
    for r in rd_by_sector:
        if not isinstance(r, dict):
            continue
        sector = r.get("sector") if isinstance(r.get("sector"), str) else None
        avg_int = _safe_float(r.get("avg_rd_intensity"))
        count = _safe_int(r.get("company_count"))
        spend = _safe_float(r.get("total_rd_spend"))
        if not sector or avg_int is None:
            continue
        sector_rows.append(
            {
                "sector": sector,
                "avg": avg_int,
                "count": count,
                "spend_b": (spend / 1e9) if isinstance(spend, float) else None,
            }
        )

    sector_rows.sort(key=lambda x: x["avg"], reverse=True)
    top = sector_rows[:8]
    body = "\n".join(
        [
            f"{_latex_escape_text(r['sector'])} & {r.get('count') or '--'} & {_fmt_pct(r.get('avg'),2)} & {_fmt_pct(r.get('spend_b'),1)} \\\\"
            for r in top
        ]
    )

    table_sector = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{R\\&D intensity concentration by sector (top sectors by average intensity)}}
\\label{{tab:rd_by_sector}}
\\begin{{tabular}}{{lrrr}}
\\toprule
Sector & Firms & Avg R\\&D intensity (\\%) & Total R\\&D spend (\\$B) \\\\
\\midrule
{body}
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_rd_by_sector.tex").write_text(table_sector, encoding="utf-8")

    # Annual premium summary table (primary inference)
    mean_premium = _safe_float(annual.get("mean_premium"))
    std_dev = _safe_float(annual.get("std_dev"))
    min_premium = _safe_float(annual.get("min_premium"))
    max_premium = _safe_float(annual.get("max_premium"))
    n_years = _safe_int(annual.get("n_years"))
    positive_years = _safe_int(annual.get("positive_years"))
    win_rate = _safe_float(annual.get("win_rate"))
    win_rate_pct = (win_rate * 100.0) if isinstance(win_rate, float) else None
    t_stat = _safe_float(hac.get("t_statistic"))
    p_val = _safe_float(hac.get("p_value"))

    table_annual = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Primary result: annual non-overlapping HML (Q5--Q1) R\\&D premium (July--June)}}
\\label{{tab:annual_hml_summary}}
\\begin{{tabular}}{{lr}}
\\toprule
Statistic & Value \\\\
\\midrule
Years (N) & {n_years or 0} \\\\
Mean premium (\\%) & {_fmt_pct(mean_premium,2)} \\\\
Std. dev. (\\%) & {_fmt_pct(std_dev,2)} \\\\
Min (\\%) & {_fmt_pct(min_premium,2)} \\\\
Max (\\%) & {_fmt_pct(max_premium,2)} \\\\
Positive years & {positive_years or 0} \\\\
Win rate (\\%) & {_fmt_pct(win_rate_pct,0)} \\\\
Newey--West t-stat (lag=1) & {_fmt_pct(t_stat,2)} \\\\
Newey--West p-value & {_fmt_p_value(p_val)} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_annual_hml_summary.tex").write_text(table_annual, encoding="utf-8")

    # Newey–West lag robustness panel (reviewer-friendly)
    nw_panel = annual.get("hac_lag_robustness") if isinstance(annual.get("hac_lag_robustness"), dict) else {}
    nw_rows = []
    for lag in [0, 1, 2, 3]:
        node = nw_panel.get(str(lag)) if isinstance(nw_panel.get(str(lag)), dict) else {}
        nw_se = _safe_float(node.get("nw_std_error"))
        nw_t = _safe_float(node.get("t_statistic"))
        nw_p = _safe_float(node.get("p_value"))
        nw_rows.append(
            f"{lag} & {_fmt_pct(nw_se,4)} & {_fmt_pct(nw_t,2)} & {_fmt_p_value(nw_p)} \\\\"
        )

    table_nw = "\n".join(
        [
            "% Auto-generated. Do not edit by hand.",
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Newey--West lag robustness for the annual HML premium}",
            "\\label{tab:nw_lag_robustness}",
            "\\begin{tabular}{lrrr}",
            "\\toprule",
            "Lag & NW SE & t-stat & p-value \\\\",
            "\\midrule",
            *nw_rows,
            "\\bottomrule",
            "\\multicolumn{4}{l}{\\footnotesize Note: primary reporting uses lag=1; this panel shows robustness for lags 0--3.}\\\\",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )

    (TABLES_DIR / "table_nw_lag_robustness.tex").write_text(table_nw, encoding="utf-8")

    # Sector-neutral annual HML premium (robustness)
    sector_neutral = payload.get("annual_hml_premium_sector_neutral") if isinstance(payload.get("annual_hml_premium_sector_neutral"), dict) else {}
    sn_hac = sector_neutral.get("hac_adjusted") if isinstance(sector_neutral.get("hac_adjusted"), dict) else {}
    sn_mean = _safe_float(sector_neutral.get("mean_premium"))
    sn_std = _safe_float(sector_neutral.get("std_dev"))
    sn_n = _safe_int(sector_neutral.get("n_years"))
    sn_pos = _safe_int(sector_neutral.get("positive_years"))
    sn_win = _safe_float(sector_neutral.get("win_rate"))
    sn_win_pct = (sn_win * 100.0) if isinstance(sn_win, float) else None
    sn_t = _safe_float(sn_hac.get("t_statistic"))
    sn_p = _safe_float(sn_hac.get("p_value"))

    table_sector_neutral = "\n".join(
        [
            "% Auto-generated. Do not edit by hand.",
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Sector-neutral annual HML premium (within-sector quintiles; equal-weight across sectors)}",
            "\\label{tab:sector_neutral_hml}",
            "\\begin{tabular}{lr}",
            "\\toprule",
            "Statistic & Value \\\\",
            "\\midrule",
            f"Years (N) & {sn_n or 0} \\\\",
            f"Mean premium (\\%) & {_fmt_pct(sn_mean,2)} \\\\",
            f"Std. dev. (\\%) & {_fmt_pct(sn_std,2)} \\\\",
            f"Positive years & {sn_pos or 0} \\\\",
            f"Win rate (\\%) & {_fmt_pct(sn_win_pct,0)} \\\\",
            f"Newey--West t-stat (lag=1) & {_fmt_pct(sn_t,2)} \\\\",
            f"Newey--West p-value & {_fmt_p_value(sn_p)} \\\\",
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )

    (TABLES_DIR / "table_sector_neutral_hml.tex").write_text(table_sector_neutral, encoding="utf-8")

    # Rolling window summaries (descriptive)
    def _horizon_row(h: str) -> dict[str, Any] | None:
        node = stats.get(h)
        if not isinstance(node, dict):
            return None
        means = node.get("quintile_means") if isinstance(node.get("quintile_means"), dict) else {}
        q1 = _safe_float(means.get("Q1"))
        q5 = _safe_float(means.get("Q5"))
        premium = (q5 - q1) if (q1 is not None and q5 is not None) else None
        return {"h": h, "q5": q5, "q1": q1, "premium": premium}

    horizon_rows = [r for r in (_horizon_row("5yr"), _horizon_row("10yr"), _horizon_row("20yr")) if r]

    body_lines = "\n".join(
        [
            f"{r['h'].upper()} & {_fmt_pct(r.get('q5'),2)} & {_fmt_pct(r.get('q1'),2)} & {_fmt_pct(r.get('premium'),2)} \\\\"
            for r in horizon_rows
        ]
    )

    table_windows = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Rolling-window quintile averages (descriptive) and Q5--Q1 spread}}
\\label{{tab:rolling_windows}}
\\begin{{tabular}}{{lrrr}}
\\toprule
Window & Q5 (\\%) & Q1 (\\%) & Q5--Q1 (\\%) \\\\
\\midrule
{body_lines}
\\bottomrule
\\multicolumn{{4}}{{l}}{{\\footnotesize Note: rolling windows overlap; these summaries are descriptive. Primary inference uses Table~\\ref{{tab:annual_hml_summary}}.}}\\\\
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_rolling_windows.tex").write_text(table_windows, encoding="utf-8")

    # Transaction costs (strategy section)
    trading_cost_pct = _safe_float(tx.get("annual_trading_cost_pct"))
    gross_premium_pct = _safe_float(tx.get("gross_rd_premium_pct"))
    net_premium_pct = _safe_float(tx.get("net_rd_premium_pct"))
    capture_rate_pct = _safe_float(tx.get("premium_capture_rate_pct"))

    table_tx = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Transaction-cost calibration and net premium vs SPY (Novy--Marx \\& Velikov, 2016)}}
\\label{{tab:transaction_costs}}
\\begin{{tabular}}{{lr}}
\\toprule
Item & Value \\\\
\\midrule
Annual trading cost estimate (\\%) & {_fmt_pct(trading_cost_pct,3)} \\\\
Gross premium (\\%) & {_fmt_pct(gross_premium_pct,2)} \\\\
Net premium after costs (\\%) & {_fmt_pct(net_premium_pct,2)} \\\\
Premium capture rate (\\%) & {_fmt_pct(capture_rate_pct,1)} \\\\
\\bottomrule
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_transaction_costs.tex").write_text(table_tx, encoding="utf-8")

    # Transaction cost sensitivity band (bps per 100% turnover)
    sens = tx.get("cost_sensitivity") if isinstance(tx.get("cost_sensitivity"), list) else []
    if sens:
        lines = []
        for row in sens:
            if not isinstance(row, dict):
                continue
            bps = _safe_int(row.get("assumption_bps_per_100pct_turnover"))
            annual_cost = _safe_float(row.get("annual_trading_cost_pct"))
            net_prem = _safe_float(row.get("net_premium_pct"))
            capture = _safe_float(row.get("premium_capture_rate_pct"))
            lines.append(
                f"{bps if bps is not None else '--'} & {_fmt_pct(annual_cost,3)} & {_fmt_pct(net_prem,2)} & {_fmt_pct(capture,1)} \\\\"
            )

        table_sens = "\n".join(
            [
                "% Auto-generated. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Transaction cost sensitivity (net premium vs SPY)}",
                "\\label{tab:transaction_cost_sensitivity}",
                "\\begin{tabular}{p{5.2cm}rrr}",
                "\\toprule",
                "Cost assumption (bp per 100\\% turnover) & Annual cost (\\%) & Net prem. (\\%) & Capture (\\%) \\\\",
                "\\midrule",
                *lines,
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )

        (TABLES_DIR / "table_transaction_cost_sensitivity.tex").write_text(table_sens, encoding="utf-8")

    # Spanning tests (snapshot already provides a LaTeX table)
    spanning = payload.get("spanning_tests_full")
    if isinstance(spanning, dict) and isinstance(spanning.get("latex_table"), str):
        # The snapshot's LaTeX is close-to-ready but can include raw underscores in model names (e.g., FF3_MOM),
        # which breaks LaTeX compilation. We escape underscores in content lines, but keep \label{...} untouched:
        # label names are identifiers and must not contain backslash-commands like \_.
        raw = spanning["latex_table"].strip()
        lines = []
        for line in raw.splitlines():
            if line.lstrip().startswith(r"\label{"):
                lines.append(line)
            else:
                lines.append(line.replace("_", r"\_"))
        latex = "\n".join(lines)
        (TABLES_DIR / "table_spanning_tests_full.tex").write_text(latex + "\n", encoding="utf-8")
    else:
        err = None
        if isinstance(spanning, dict) and isinstance(spanning.get("error"), str):
            err = spanning.get("error")
        msg = _latex_escape_text(err) if isinstance(err, str) else "Unavailable in this snapshot."
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Factor spanning tests (unavailable)}",
                "\\label{tab:spanning_tests_full}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                f"Unavailable & {msg} \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_spanning_tests_full.tex").write_text(placeholder, encoding="utf-8")

    # Double-sort (Size x R&D intensity)
    ds = payload.get("double_sort_analysis")
    if isinstance(ds, dict) and isinstance(ds.get("matrix"), dict):
        matrix = ds["matrix"]
        spreads = ds.get("rd_spreads_by_size") if isinstance(ds.get("rd_spreads_by_size"), dict) else {}

        size_order = ["Large", "Medium", "Small"]
        rd_order = ["Low", "Medium", "High"]

        lines = []
        for size in size_order:
            row = matrix.get(size) if isinstance(matrix.get(size), dict) else {}
            means = []
            for rd in rd_order:
                cell = row.get(rd) if isinstance(row.get(rd), dict) else {}
                means.append(_fmt_pct(_safe_float(cell.get("mean_return")), 2))

            s = spreads.get(size) if isinstance(spreads.get(size), dict) else {}
            spread = _safe_float(s.get("high_minus_low"))
            t = _safe_float(s.get("t_stat"))
            p = _safe_float(s.get("p_value"))
            lines.append(f"{size} & {means[0]} & {means[1]} & {means[2]} & {_fmt_pct(spread,2)} & {_fmt_pct(t,2)} & {_fmt_p_value(p)} \\\\")

        table_ds = "\n".join(
            [
                "% Auto-generated. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Double-sort: Size \\texttimes{} R\\&D intensity (mean returns, \\%)}",
                "\\label{tab:double_sort}",
                "\\begin{tabular}{lrrrrrr}",
                "\\toprule",
                "Size bucket & Low R\\&D & Medium R\\&D & High R\\&D & High--Low & t-stat & p-value \\\\",
                "\\midrule",
                *lines,
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )

        (TABLES_DIR / "table_double_sort.tex").write_text(table_ds, encoding="utf-8")
    else:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Double-sort: Size \\texttimes{} R\\&D intensity (unavailable)}",
                "\\label{tab:double_sort}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Double-sort payload missing or invalid in this snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_double_sort.tex").write_text(placeholder, encoding="utf-8")

    # Delisting sensitivity scenarios (simulated)
    sens = payload.get("delisting_sensitivity")
    if isinstance(sens, dict) and isinstance(sens.get("results"), dict):
        results = sens["results"]
        order = ["baseline", "conservative", "moderate", "aggressive"]
        lines = []
        for k in order:
            node = results.get(k)
            if not isinstance(node, dict):
                continue
            ann = node.get("annual_hml") if isinstance(node.get("annual_hml"), dict) else {}
            mean_p = _safe_float(ann.get("mean_premium_pct"))
            t = _safe_float(ann.get("t_statistic"))
            p = _safe_float(ann.get("p_value"))
            delta = _safe_float(ann.get("delta_vs_baseline_pct"))
            name_raw = node.get("name") if isinstance(node.get("name"), str) else k
            name = _latex_escape_text(name_raw)
            lines.append(f"{name} & {_fmt_pct(mean_p,2)} & {_fmt_pct(delta,2)} & {_fmt_pct(t,2)} & {_fmt_p_value(p)} \\\\")

        table_sens = "\n".join(
            [
                "% Auto-generated. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Delisting adjustment sensitivity (simulated; see snapshot note)}",
                "\\label{tab:delisting_sensitivity}",
                "\\begin{tabular}{lrrrr}",
                "\\toprule",
                "Scenario & Mean premium (\\%) & $\\Delta$ vs baseline (\\%) & t-stat & p-value \\\\",
                "\\midrule",
                *lines,
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )

        (TABLES_DIR / "table_delisting_sensitivity.tex").write_text(table_sens, encoding="utf-8")
    else:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Delisting adjustment sensitivity (unavailable)}",
                "\\label{tab:delisting_sensitivity}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Delisting sensitivity payload missing or invalid in this snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_delisting_sensitivity.tex").write_text(placeholder, encoding="utf-8")

    # Mispricing tests (arbitrage cost proxies) — descriptive
    mis = payload.get("mispricing_tests")
    if isinstance(mis, dict) and isinstance(mis.get("tests"), dict):
        tests = mis["tests"]

        def _emit_group(group_name: str, d: dict[str, Any]) -> list[str]:
            lines2 = []
            for k, v in d.items():
                if not isinstance(v, dict):
                    continue
                premium = _safe_float(v.get("premium"))
                n = _safe_int(v.get("n_obs"))
                lines2.append(f"{group_name}: {k} & {_fmt_pct(premium,2)} & {n or '--'} \\\\")
            return lines2

        lines = []
        if isinstance(tests.get("by_size"), dict):
            lines.extend(_emit_group("Size", tests["by_size"]))
        if isinstance(tests.get("by_volatility"), dict):
            lines.extend(_emit_group("Volatility", tests["by_volatility"]))
        # Coverage proxy excluded from paper: uses years_tracked (not true analyst coverage)
        # and one tercile ("High") lacks sufficient within-quintile variation for R&D premium.
        # if isinstance(tests.get("by_coverage"), dict):
        #     lines.extend(_emit_group("Coverage", tests["by_coverage"]))

        table_mis = "\n".join(
            [
                "% Auto-generated. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{R\\&D premium by arbitrage-cost proxies (descriptive)}",
                "\\label{tab:mispricing_tests}",
                "\\begin{tabular}{lrr}",
                "\\toprule",
                "Group & Premium (\\%) & N \\\\",
                "\\midrule",
                *lines,
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )

        (TABLES_DIR / "table_mispricing_tests.tex").write_text(table_mis, encoding="utf-8")
    else:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{R\\&D premium by arbitrage-cost proxies (unavailable)}",
                "\\label{tab:mispricing_tests}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Mispricing tests payload missing or invalid in this snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_mispricing_tests.tex").write_text(placeholder, encoding="utf-8")


def write_annual_hml_detail_table(payload: dict[str, Any]) -> None:
    """
    Writes a detailed year-by-year annual HML premium table showing all individual years.
    """
    annual = payload.get("annual_hml_premium")
    if not isinstance(annual, dict):
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Year-by-year annual HML premium (unavailable)}",
                "\\label{tab:annual_hml_detail}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Missing annual\\_hml\\_premium in snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_annual_hml_detail.tex").write_text(placeholder, encoding="utf-8")
        return
    rows = annual.get("annual_premiums")
    if not isinstance(rows, list):
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Year-by-year annual HML premium (unavailable)}",
                "\\label{tab:annual_hml_detail}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Missing annual\\_premiums list in snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_annual_hml_detail.tex").write_text(placeholder, encoding="utf-8")
        return

    parsed: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        fy = _safe_int(r.get("formation_year"))
        q1 = _safe_float(r.get("q1_return"))
        q5 = _safe_float(r.get("q5_return"))
        hml = _safe_float(r.get("hml_premium"))
        label = r.get("year") if isinstance(r.get("year"), str) else ""
        if fy is None or hml is None:
            continue
        parsed.append({
            "formation_year": fy,
            "label": label.replace("-", "--"),
            "q1": q1,
            "q5": q5,
            "hml": hml,
        })

    parsed.sort(key=lambda x: x["formation_year"])
    if not parsed:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Year-by-year annual HML premium (unavailable)}",
                "\\label{tab:annual_hml_detail}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Annual HML detail could not be parsed from snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_annual_hml_detail.tex").write_text(placeholder, encoding="utf-8")
        return

    # Build table rows
    body_lines = []
    for r in parsed:
        sign = "+" if (r["hml"] or 0) >= 0 else ""
        body_lines.append(
            f"{r['label']} & {_fmt_pct(r.get('q1'), 2)} & {_fmt_pct(r.get('q5'), 2)} & {sign}{_fmt_pct(r.get('hml'), 2)} \\\\"
        )

    table = f"""% Auto-generated. Do not edit by hand.
\\begin{{longtable}}{{lrrr}}
\\caption{{Year-by-year annual HML premium (Q5--Q1) detail}} \\label{{tab:annual_hml_detail}} \\\\
\\toprule
Return period & Q1 (\\%) & Q5 (\\%) & HML (\\%) \\\\
\\midrule
\\endfirsthead
\\caption[]{{Year-by-year annual HML premium (continued)}} \\\\
\\toprule
Return period & Q1 (\\%) & Q5 (\\%) & HML (\\%) \\\\
\\midrule
\\endhead
\\midrule
\\multicolumn{{4}}{{r}}{{\\footnotesize Continued on next page}} \\\\
\\endfoot
\\bottomrule
\\endlastfoot
{chr(10).join(body_lines)}
\\end{{longtable}}
"""

    (TABLES_DIR / "table_annual_hml_detail.tex").write_text(table, encoding="utf-8")


def write_liquidity_moderation_table(payload: dict[str, Any]) -> None:
    """
    Writes `tables/table_liquidity_moderation.tex`.

    WHY:
      Reviewer-friendly robustness check motivated by Ahmed, Bu, and Ye (2025):
      the R&D premium may strengthen with illiquidity (information frictions).

    SOURCE:
      Uses `payload["liquidity_moderation"]` produced by the publication snapshot.
    """
    node = payload.get("liquidity_moderation")
    if not isinstance(node, dict) or "error" in node:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{Illiquidity moderation of the R\\&D premium (unavailable)}",
                "\\label{tab:liquidity_moderation}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Liquidity moderation payload missing or invalid in this snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_liquidity_moderation.tex").write_text(placeholder, encoding="utf-8")
        return

    meta = node.get("meta") if isinstance(node.get("meta"), dict) else {}
    amihud = node.get("amihud") if isinstance(node.get("amihud"), dict) else {}
    dvol = node.get("dollar_volume") if isinstance(node.get("dollar_volume"), dict) else {}

    def _row(panel: str, bucket: str, b: dict[str, Any]) -> str:
        prem = _safe_float(b.get("mean_premium_pct"))
        t = _safe_float(b.get("nw_t_stat"))
        n_years = _safe_int(b.get("n_years"))
        avg_firms = _safe_float(b.get("avg_firms_per_year"))
        return (
            f"{panel} & {bucket} & {_fmt_pct(prem, 2)} & {(_fmt_pct(t, 2) if t is not None else '--')} & "
            f"{(n_years if n_years is not None else '--')} & "
            f"{(_fmt_pct(avg_firms, 1) if avg_firms is not None else '--')} \\\\"
        )

    lines: list[str] = []

    # Panel A: Amihud
    a_buckets = amihud.get("buckets") if isinstance(amihud.get("buckets"), dict) else {}
    for b in ["Liquid", "Medium", "Illiquid"]:
        if isinstance(a_buckets.get(b), dict):
            lines.append(_row("Amihud", b, a_buckets[b]))
    if isinstance(a_buckets.get("Illiquid_minus_Liquid"), dict):
        lines.append(_row("Amihud", "Illiquid − Liquid", a_buckets["Illiquid_minus_Liquid"]))

    lines.append("\\addlinespace")

    # Panel B: Dollar volume
    d_buckets = dvol.get("buckets") if isinstance(dvol.get("buckets"), dict) else {}
    for b in ["Liquid", "Medium", "Illiquid"]:
        if isinstance(d_buckets.get(b), dict):
            lines.append(_row("Dollar volume", b, d_buckets[b]))
    if isinstance(d_buckets.get("Illiquid_minus_Liquid"), dict):
        lines.append(_row("Dollar volume", "Illiquid − Liquid", d_buckets["Illiquid_minus_Liquid"]))

    start_y = _safe_int(meta.get("start_formation_year"))
    end_y = _safe_int(meta.get("end_formation_year"))
    window = meta.get("liquidity_window") if isinstance(meta.get("liquidity_window"), str) else "pre-formation"
    lags = _safe_int(meta.get("nw_lags"))
    caption_suffix = f"({start_y}-{end_y}; {window}; Newey--West lags={lags})" if start_y and end_y and lags else ""

    table = "\n".join(
        [
            "% Auto-generated. Do not edit by hand.",
            "\\begin{table}[htbp]",
            "\\centering",
            f\"\\caption{{Illiquidity moderation of the R\\&D premium (descriptive) {caption_suffix}}}\",
            "\\label{tab:liquidity_moderation}",
            "\\begin{tabular}{llrrrr}",
            "\\toprule",
            "Proxy & Bucket & Premium (\\%) & NW $t$ & N years & Avg firms/year \\\\",
            "\\midrule",
            *lines,
            "\\bottomrule",
            "\\multicolumn{6}{l}{\\footnotesize Premium is within-bucket Q5$-$Q1 using July--June annualized returns.} \\\\",
            "\\multicolumn{6}{l}{\\footnotesize Amihud (2002) uses daily |return| / dollar volume; dollar volume bucket uses avg(close$\\times$volume).} \\\\",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
    )

    (TABLES_DIR / "table_liquidity_moderation.tex").write_text(table, encoding="utf-8")


def write_regime_breakdown_table(payload: dict[str, Any]) -> None:
    """
    Writes a regime/subperiod breakdown table showing premium by market era.
    """
    annual = payload.get("annual_hml_premium")
    if not isinstance(annual, dict):
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{R\\&D premium by market regime (unavailable)}",
                "\\label{tab:regime_breakdown}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Missing annual\\_hml\\_premium in snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_regime_breakdown.tex").write_text(placeholder, encoding="utf-8")
        return
    rows = annual.get("annual_premiums")
    if not isinstance(rows, list):
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{R\\&D premium by market regime (unavailable)}",
                "\\label{tab:regime_breakdown}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Missing annual\\_premiums list in snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_regime_breakdown.tex").write_text(placeholder, encoding="utf-8")
        return

    # Parse annual data
    parsed: list[dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        fy = _safe_int(r.get("formation_year"))
        q1 = _safe_float(r.get("q1_return"))
        q5 = _safe_float(r.get("q5_return"))
        hml = _safe_float(r.get("hml_premium"))
        if fy is None or hml is None:
            continue
        # Return period starts in formation_year + 1 (July)
        return_start = fy + 1
        parsed.append({
            "return_start": return_start,
            "q1": q1,
            "q5": q5,
            "hml": hml,
        })

    if not parsed:
        placeholder = "\n".join(
            [
                "% Auto-generated placeholder. Do not edit by hand.",
                "\\begin{table}[htbp]",
                "\\centering",
                "\\caption{R\\&D premium by market regime (unavailable)}",
                "\\label{tab:regime_breakdown}",
                "\\begin{tabular}{lp{10cm}}",
                "\\toprule",
                "Status & Details \\\\",
                "\\midrule",
                "Unavailable & Regime breakdown could not be parsed from snapshot. \\\\",
                "\\bottomrule",
                "\\end{tabular}",
                "\\end{table}",
                "",
            ]
        )
        (TABLES_DIR / "table_regime_breakdown.tex").write_text(placeholder, encoding="utf-8")
        return

    # Define regimes based on return period start year
    years = [r["return_start"] for r in parsed]
    max_year = max(years) if years else 2024

    regimes = [
        {"label": "2001--2002", "start": 2001, "end": 2002, "event": "Post-dot-com"},
        {"label": "2003--2007", "start": 2003, "end": 2007, "event": "Pre-GFC expansion"},
        {"label": "2008--2009", "start": 2008, "end": 2009, "event": "Financial Crisis"},
        {"label": "2010--2016", "start": 2010, "end": 2016, "event": "Post-GFC recovery"},
        {"label": f"2017--{max_year}", "start": 2017, "end": max_year, "event": "Recent era"},
    ]

    body_lines = []
    for regime in regimes:
        subset = [r for r in parsed if regime["start"] <= r["return_start"] <= regime["end"]]
        if not subset:
            continue

        n = len(subset)
        mean_hml = sum(r["hml"] for r in subset) / n if n else 0
        mean_q1 = sum(r["q1"] for r in subset if r["q1"] is not None) / len([r for r in subset if r["q1"] is not None]) if any(r["q1"] is not None for r in subset) else None
        mean_q5 = sum(r["q5"] for r in subset if r["q5"] is not None) / len([r for r in subset if r["q5"] is not None]) if any(r["q5"] is not None for r in subset) else None
        pos_years = sum(1 for r in subset if r["hml"] > 0)
        win_rate = (pos_years / n * 100) if n else 0

        body_lines.append(
            f"{regime['label']} & {regime['event']} & {n} & {_fmt_pct(mean_q1, 1)} & {_fmt_pct(mean_q5, 1)} & {_fmt_pct(mean_hml, 1)} & {_fmt_pct(win_rate, 0)} \\\\"
        )

    table = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{R\\&D premium by market regime (descriptive)}}
\\label{{tab:regime_breakdown}}
\\begin{{tabular}}{{llrrrrr}}
\\toprule
Period & Market context & N & Q1 (\\%) & Q5 (\\%) & HML (\\%) & Win (\\%) \\\\
\\midrule
{chr(10).join(body_lines)}
\\bottomrule
\\multicolumn{{7}}{{l}}{{\\footnotesize Note: Win (\\%) shows the fraction of years with positive HML premium within each regime.}} \\\\
\\end{{tabular}}
\\end{{table}}
"""

    (TABLES_DIR / "table_regime_breakdown.tex").write_text(table, encoding="utf-8")


def write_universe_integrity_table(payload: dict[str, Any]) -> None:
    """
    Generate Universe Integrity table from membership_diagnostics.
    
    WHY:
      JPM reviewers want proof that point-in-time membership is enforced.
      This table shows per-year constituent counts, source breakdown, and summary stats.
    """
    md = payload.get("membership_diagnostics", {})
    if not isinstance(md, dict):
        placeholder = "\n".join([
            "% Auto-generated placeholder. Do not edit by hand.",
            "\\begin{table}[htbp]",
            "\\centering",
            "\\caption{Universe integrity diagnostics (unavailable)}",
            "\\label{tab:universe_integrity}",
            "\\begin{tabular}{lp{10cm}}",
            "\\toprule",
            "Status & Details \\\\",
            "\\midrule",
            "Unavailable & membership\\_diagnostics not present in snapshot. \\\\",
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ])
        (TABLES_DIR / "table_universe_integrity.tex").write_text(placeholder, encoding="utf-8")
        return
    
    summary = md.get("summary", {})
    per_year = md.get("per_year", {})
    
    # Extract summary stats
    avg_const = summary.get("avg_constituents_per_year", 0)
    min_const = summary.get("min_constituents_per_year", 0)
    max_const = summary.get("max_constituents_per_year", 0)
    union_tickers = summary.get("unique_tickers_union", 0)
    n_additions = summary.get("n_additions_spans", 0)
    n_removals = summary.get("n_removals_spans", 0)
    sources = summary.get("membership_source_totals", {})
    
    # Build source breakdown string
    source_items = []
    for src, cnt in sources.items():
        src_display = src.replace("_", "\\_")
        source_items.append(f"{src_display}: {cnt}")
    source_str = "; ".join(source_items) if source_items else "N/A"
    
    # Build per-year summary (show selected years to avoid huge table)
    years_to_show = ["2001", "2005", "2010", "2015", "2020", "2024"]
    year_rows = []
    for y in years_to_show:
        yd = per_year.get(y, {})
        if yd:
            n = yd.get("n_constituents", 0)
            year_rows.append(f"Jul {y} & {n}")
    
    year_samples = " \\\\\n".join(year_rows) if year_rows else "N/A"
    
    table = f"""% Auto-generated. Do not edit by hand.
\\begin{{table}}[htbp]
\\centering
\\caption{{Universe integrity: index eligibility gating (Tier-1)}}
\\label{{tab:universe_integrity}}
\\begin{{tabular}}{{p{{0.41\\textwidth}}p{{0.52\\textwidth}}}}
\\toprule
Diagnostic & Value \\\\
\\midrule
Avg.~constituents per formation year & {avg_const:.1f} \\\\
Min / Max constituents & {min_const} / {max_const} \\\\
Union of unique tickers & {union_tickers} \\\\
Addition spans tracked & {n_additions} \\\\
Removal spans tracked & {n_removals} \\\\
Membership sources & {source_str} \\\\
\\midrule
\\multicolumn{{2}}{{l}}{{\\textbf{{Sample formation years:}}}} \\\\
{year_samples} \\\\
\\bottomrule
\\multicolumn{{2}}{{p{{0.93\\textwidth}}}}{{\\footnotesize Note: Counts reflect the eligible subset of the current S\\&P 500 list at each July 1 formation date (based on ``Date added'').}} \\\\
\\multicolumn{{2}}{{p{{0.93\\textwidth}}}}{{\\footnotesize Limitation: removals and historical constituents not in the current list are not tracked in Tier-1.}} \\\\
\\multicolumn{{2}}{{p{{0.93\\textwidth}}}}{{\\footnotesize Source: Wikipedia S\\&P 500 constituents list; ``Date added'' compiled from S\\&P Dow Jones announcements.}} \\\\
\\end{{tabular}}
\\end{{table}}
"""
    
    (TABLES_DIR / "table_universe_integrity.tex").write_text(table, encoding="utf-8")


def main() -> None:
    _ensure_dirs()
    if not SNAPSHOT_PATH.exists():
        raise FileNotFoundError(f"Missing snapshot: {SNAPSHOT_PATH}")

    meta, payload = _read_snapshot()

    write_metrics_tex(meta, payload)
    write_rd_trends_csv(payload)
    write_annual_hml_csv(payload)
    write_annual_quintile_growth_csv(payload)
    write_factor_premiums_csv(payload)
    write_quintile_means_csv(payload)
    write_investable_growth_csv(payload)
    write_tables(meta, payload)
    write_annual_hml_detail_table(payload)
    write_liquidity_moderation_table(payload)
    write_regime_breakdown_table(payload)
    write_universe_integrity_table(payload)

    print("✅ Generated assets:")
    print(f"- {DATA_DIR / 'metrics.tex'}")
    print(f"- {DATA_DIR / 'rd_trends.csv'}")
    print(f"- {DATA_DIR / 'annual_hml_premium.csv'}")
    print(f"- {DATA_DIR / 'annual_quintile_growth.csv'}")
    print(f"- {DATA_DIR / 'factor_premiums.csv'}")
    print(f"- {DATA_DIR / 'quintile_means_5yr.csv'} / 10yr / 20yr")
    print(f"- {DATA_DIR / 'investable_growth.csv'}")
    print(f"- {TABLES_DIR}/*.tex")
    print(f"- {TABLES_DIR}/table_annual_hml_detail.tex")
    print(f"- {TABLES_DIR}/table_liquidity_moderation.tex")
    print(f"- {TABLES_DIR}/table_regime_breakdown.tex")


if __name__ == "__main__":
    main()


