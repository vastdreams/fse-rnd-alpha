#!/usr/bin/env python3
"""Create an immutable, evidence-only coverage report for a sealed universe.

The report records what exists for a particular universe version; it never
backfills values, turns an unknown into a pass, or makes a release decision.
Operators must rebuild and seal a new universe after a verified backfill
cohort instead of rewriting this report in place.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = ROOT / "data"
SOURCE_SHA_RE = re.compile(r"[0-9a-f]{40}")
CHECKSUM_RE = re.compile(r"[0-9a-f]{64}")
COVERAGE_DOMAINS = (
    "financials_cache",
    "filing_text_cache",
    "filing_source_evidence",
    "filing_map",
    "measured_text_stance",
    "valid_fair_value_band",
)
REQUIRED_POLICY = {
    "unknowns_are_fail_closed": True,
    "backfill_requires_new_sealed_universe": True,
    "report_contains_source_evidence_status_only": True,
}


def _canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    return {}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _metric_value(vector: dict[str, Any], field: str) -> float | None:
    metric = vector.get(field)
    if not isinstance(metric, dict):
        return None
    return _number(metric.get("value"))


def _valid_fair_value_band(vector: dict[str, Any]) -> bool:
    lo = _metric_value(vector, "fair_px_lo")
    med = _metric_value(vector, "fair_px_med")
    hi = _metric_value(vector, "fair_px_hi")
    return lo is not None and med is not None and hi is not None and 0 < lo <= med <= hi


def _nonempty_file(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def _coverage(tickers: Iterable[str], present: Iterable[str]) -> dict[str, Any]:
    universe = sorted(set(tickers))
    present_set = set(present)
    missing = [ticker for ticker in universe if ticker not in present_set]
    count = len(universe)
    return {
        "present": count - len(missing),
        "missing": len(missing),
        "coverage_pct": round(100 * (count - len(missing)) / count, 1) if count else 0.0,
        "missing_tickers": missing,
    }


def build_report(
    *,
    build: dict[str, Any],
    rows: list[dict[str, Any]],
    data_dir: Path,
) -> dict[str, Any]:
    """Build a deterministic report from sealed rows and cache-file presence."""

    universe_version = str(build["universe_version"])
    source_sha = str(build["source_sha"])
    row_by_ticker = {str(row["ticker"]).upper(): row for row in rows}
    if len(row_by_ticker) != len(rows):
        raise ValueError("Coverage input has duplicate tickers")
    tickers = sorted(row_by_ticker)

    financial_cache = [
        ticker
        for ticker in tickers
        if _nonempty_file(data_dir / "financials_cache" / f"{ticker}.json")
    ]
    filing_cache = [
        ticker
        for ticker in tickers
        if _nonempty_file(data_dir / "filings_cache" / f"{ticker}.txt")
    ]
    filing_evidence = [
        ticker for ticker, row in row_by_ticker.items() if bool(row.get("has_filing_evidence"))
    ]
    filing_maps = [
        ticker for ticker, row in row_by_ticker.items() if bool(row.get("has_filing_map"))
    ]
    text_stance = [
        ticker
        for ticker, row in row_by_ticker.items()
        if _metric_value(_json_object(row.get("vector")), "ai_text_stance") is not None
    ]
    valid_bands = [
        ticker
        for ticker, row in row_by_ticker.items()
        if _valid_fair_value_band(_json_object(row.get("vector")))
    ]
    kill_active = sorted(
        ticker for ticker, row in row_by_ticker.items() if row.get("kill_active") is True
    )
    kill_inactive = sorted(
        ticker for ticker, row in row_by_ticker.items() if row.get("kill_active") is False
    )
    kill_unknown = sorted(
        ticker for ticker, row in row_by_ticker.items() if row.get("kill_active") is None
    )
    grades: dict[str, int] = {}
    for row in rows:
        grade = str(row.get("completeness_grade") or "Unknown")
        grades[grade] = grades.get(grade, 0) + 1

    content: dict[str, Any] = {
        "schema_version": 1,
        "universe_version": universe_version,
        "source_sha": source_sha,
        "build_input_sha256": build.get("input_sha256"),
        "sealed_at": str(build.get("sealed_at") or ""),
        "universe_tickers": len(tickers),
        "coverage": {
            "financials_cache": _coverage(tickers, financial_cache),
            "filing_text_cache": _coverage(tickers, filing_cache),
            "filing_source_evidence": _coverage(tickers, filing_evidence),
            "filing_map": _coverage(tickers, filing_maps),
            "measured_text_stance": _coverage(tickers, text_stance),
            "valid_fair_value_band": _coverage(tickers, valid_bands),
            "kill_state": {
                "explicit_inactive": len(kill_inactive),
                "explicit_active": len(kill_active),
                "unknown": len(kill_unknown),
                "active_tickers": kill_active,
                "unknown_tickers": kill_unknown,
            },
            "completeness_grade": dict(sorted(grades.items())),
        },
        "policy": {
            "unknowns_are_fail_closed": True,
            "backfill_requires_new_sealed_universe": True,
            "report_contains_source_evidence_status_only": True,
        },
    }
    payload = {
        **content,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    payload["report_sha256"] = hashlib.sha256(_canonical_json(content)).hexdigest()
    return payload


async def load_coverage_inputs(
    database_url: str, universe_version: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Load only the sealed version's metadata and evidence-presence flags."""

    import asyncpg

    dsn = database_url.replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(dsn)
    try:
        build_record = await connection.fetchrow(
            """
            SELECT universe_version, source_sha, input_sha256, sealed_at, status
              FROM universe_builds
             WHERE universe_version=$1
            """,
            universe_version,
        )
        if build_record is None:
            raise RuntimeError(f"Unknown universe version: {universe_version}")
        build = dict(build_record)
        if build.get("status") != "sealed":
            raise RuntimeError(f"Universe version is not sealed: {universe_version}")
        if not SOURCE_SHA_RE.fullmatch(str(build.get("source_sha") or "")):
            raise RuntimeError("Sealed universe has no committed 40-character source SHA")

        records = await connection.fetch(
            """
            WITH filing_evidence AS (
                SELECT DISTINCT snapshot.ticker
                  FROM source_snapshots AS snapshot
                  JOIN evidence_claims AS claim
                    ON claim.snapshot_id = snapshot.snapshot_id
                  JOIN universe_evidence_refs AS ref
                    ON ref.claim_id = claim.claim_id
                 WHERE ref.universe_version=$1
                   AND snapshot.kind='10-K'
            ),
            filing_maps AS (
                SELECT DISTINCT ticker
                  FROM deepseek_audit_runs
                 WHERE universe_version=$1
                   AND job='filing_map'
                   AND status IN ('mapped', 'confirmed')
            )
            SELECT vector_row.ticker,
                   vector_row.vector,
                   vector_row.completeness_grade,
                   vector_row.kill_active,
                   filing_evidence.ticker IS NOT NULL AS has_filing_evidence,
                   filing_maps.ticker IS NOT NULL AS has_filing_map
              FROM metric_vectors AS vector_row
              LEFT JOIN filing_evidence ON filing_evidence.ticker=vector_row.ticker
              LEFT JOIN filing_maps ON filing_maps.ticker=vector_row.ticker
             WHERE vector_row.universe_version=$1
             ORDER BY vector_row.ticker
            """,
            universe_version,
        )
        return build, [dict(record) for record in records]
    finally:
        await connection.close()


def _report_content(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"generated_at", "report_sha256"}
    }


def _require_count(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"Coverage report has invalid {name}")
    return value


def _validate_coverage_domain(name: str, value: Any, universe_tickers: int) -> None:
    if not isinstance(value, dict):
        raise RuntimeError(f"Coverage report has no {name} domain")
    present = _require_count(value.get("present"), name=f"{name}.present")
    missing = _require_count(value.get("missing"), name=f"{name}.missing")
    missing_tickers = value.get("missing_tickers")
    if not isinstance(missing_tickers, list) or not all(
        isinstance(ticker, str) and ticker and ticker == ticker.upper()
        for ticker in missing_tickers
    ):
        raise RuntimeError(f"Coverage report has invalid {name}.missing_tickers")
    if sorted(set(missing_tickers)) != missing_tickers or len(missing_tickers) != missing:
        raise RuntimeError(f"Coverage report has inconsistent {name}.missing_tickers")
    if present + missing != universe_tickers:
        raise RuntimeError(f"Coverage report has inconsistent {name} totals")
    coverage_pct = value.get("coverage_pct")
    expected_pct = round(100 * present / universe_tickers, 1) if universe_tickers else 0.0
    if (
        isinstance(coverage_pct, bool)
        or not isinstance(coverage_pct, (int, float))
        or not math.isfinite(float(coverage_pct))
        or float(coverage_pct) != expected_pct
    ):
        raise RuntimeError(f"Coverage report has inconsistent {name}.coverage_pct")


def validate_report(
    report: dict[str, Any],
    *,
    expected_universe_version: str | None = None,
    expected_source_sha: str | None = None,
) -> None:
    """Validate the complete evidence schema before it can enter a release."""

    if report.get("schema_version") != 1:
        raise RuntimeError(f"Unsupported coverage report schema: {report.get('schema_version')!r}")
    universe_version = report.get("universe_version")
    if not isinstance(universe_version, str) or not universe_version:
        raise RuntimeError("Coverage report has no universe version")
    if expected_universe_version and universe_version != expected_universe_version:
        raise RuntimeError("Coverage report universe version does not match the staged release")
    source_sha = report.get("source_sha")
    if not isinstance(source_sha, str) or not SOURCE_SHA_RE.fullmatch(source_sha):
        raise RuntimeError("Coverage report has no committed source SHA")
    if expected_source_sha and source_sha != expected_source_sha:
        raise RuntimeError("Coverage report source SHA does not match the staged release")
    if not isinstance(report.get("build_input_sha256"), str) or not CHECKSUM_RE.fullmatch(
        report["build_input_sha256"]
    ):
        raise RuntimeError("Coverage report has no build-input checksum")
    if not isinstance(report.get("sealed_at"), str) or not report["sealed_at"]:
        raise RuntimeError("Coverage report has no seal timestamp")
    if not isinstance(report.get("generated_at"), str) or not report["generated_at"]:
        raise RuntimeError("Coverage report has no generation timestamp")
    universe_tickers = _require_count(report.get("universe_tickers"), name="universe_tickers")
    if universe_tickers == 0:
        raise RuntimeError("Coverage report has no universe tickers")

    coverage = report.get("coverage")
    if not isinstance(coverage, dict):
        raise RuntimeError("Coverage report has no coverage object")
    for name in COVERAGE_DOMAINS:
        _validate_coverage_domain(name, coverage.get(name), universe_tickers)

    kill_state = coverage.get("kill_state")
    if not isinstance(kill_state, dict):
        raise RuntimeError("Coverage report has no kill-state coverage")
    explicit_inactive = _require_count(
        kill_state.get("explicit_inactive"), name="kill_state.explicit_inactive"
    )
    explicit_active = _require_count(
        kill_state.get("explicit_active"), name="kill_state.explicit_active"
    )
    unknown = _require_count(kill_state.get("unknown"), name="kill_state.unknown")
    for field, count in (("active_tickers", explicit_active), ("unknown_tickers", unknown)):
        tickers = kill_state.get(field)
        if not isinstance(tickers, list) or sorted(set(tickers)) != tickers or len(tickers) != count:
            raise RuntimeError(f"Coverage report has inconsistent kill_state.{field}")
    if explicit_inactive + explicit_active + unknown != universe_tickers:
        raise RuntimeError("Coverage report has inconsistent kill-state totals")

    grades = coverage.get("completeness_grade")
    if not isinstance(grades, dict) or sum(
        _require_count(value, name=f"completeness_grade.{key}") for key, value in grades.items()
    ) != universe_tickers:
        raise RuntimeError("Coverage report has inconsistent completeness grades")

    policy = report.get("policy")
    if not isinstance(policy, dict) or any(
        policy.get(name) is not expected for name, expected in REQUIRED_POLICY.items()
    ):
        raise RuntimeError("Coverage report has an invalid fail-closed policy")

    actual_checksum = hashlib.sha256(_canonical_json(_report_content(report))).hexdigest()
    if report.get("report_sha256") != actual_checksum:
        raise RuntimeError("Coverage report checksum does not match its contents")


def verify_report(
    report: dict[str, Any],
    *,
    build: dict[str, Any],
    rows: list[dict[str, Any]],
    data_dir: Path,
) -> None:
    """Prove the report equals a fresh computation over sealed rows and staged data."""

    validate_report(
        report,
        expected_universe_version=str(build["universe_version"]),
        expected_source_sha=str(build["source_sha"]),
    )
    expected = build_report(build=build, rows=rows, data_dir=data_dir)
    if _report_content(report) != _report_content(expected):
        raise RuntimeError(
            "Coverage report does not match sealed research rows and the staged data snapshot"
        )


def write_immutable_report(output: Path, report: dict[str, Any]) -> None:
    """Write once, or accept a byte-equivalent coverage result on rerun."""

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        existing = json.loads(output.read_text())
        if existing.get("report_sha256") == report["report_sha256"] and _report_content(
            existing
        ) == _report_content(report):
            return
        raise RuntimeError(
            f"Coverage report already exists with different contents: {output}. "
            "Backfill evidence, rebuild and seal a new universe version instead of rewriting it."
        )

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output.parent, prefix=f".{output.name}.", delete=False
    ) as temporary:
        temporary.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a versioned evidence coverage report for a sealed universe"
    )
    parser.add_argument("--universe-version")
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--expected-source-sha")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--validate-report", type=Path)
    action.add_argument("--verify-report", type=Path)
    args = parser.parse_args()

    if args.validate_report:
        report = json.loads(args.validate_report.read_text())
        validate_report(
            report,
            expected_universe_version=args.universe_version,
            expected_source_sha=args.expected_source_sha,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return
    if not args.universe_version:
        parser.error("--universe-version is required when generating or verifying a report")
    if not args.database_url:
        raise SystemExit("--database-url or DATABASE_URL is required")
    build, rows = asyncio.run(load_coverage_inputs(args.database_url, args.universe_version))
    if not rows:
        raise SystemExit(f"Sealed universe has no metric vectors: {args.universe_version}")

    if args.verify_report:
        report = json.loads(args.verify_report.read_text())
        verify_report(report, build=build, rows=rows, data_dir=args.data_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return

    output = args.output or args.data_dir / "coverage_reports" / f"{args.universe_version}.json"
    report = build_report(build=build, rows=rows, data_dir=args.data_dir)
    write_immutable_report(output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
