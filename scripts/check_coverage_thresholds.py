#!/usr/bin/env python3
"""
PATH: scripts/check_coverage_thresholds.py
PURPOSE: Fail-closed coverage floor against a coverage report JSON.

Usage:
  python3 scripts/check_coverage_thresholds.py path/to/coverage_report.json
  python3 scripts/check_coverage_thresholds.py --self-test
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THRESH = ROOT / "contracts" / "coverage-thresholds.json"


def check(report: dict, thresholds: dict) -> list[str]:
    errors: list[str] = []
    domains = {d.get("id"): d for d in report.get("domains") or []}
    for req in thresholds.get("domains") or []:
        rid = req["id"]
        need = float(req["min_coverage_pct"])
        row = domains.get(rid)
        if not row:
            errors.append(f"missing domain {rid}")
            continue
        got = float(row.get("coverage_pct", -1))
        if got < need:
            errors.append(f"{rid}: coverage_pct {got} < min {need}")
    return errors


def main() -> int:
    thresholds = json.loads(THRESH.read_text())
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        ok_report = {
            "domains": [
                {"id": "filing_fetched", "coverage_pct": 80},
                {"id": "fair_band_present", "coverage_pct": 55},
                {"id": "stance_analyzed", "coverage_pct": 20},
            ]
        }
        bad_report = {
            "domains": [
                {"id": "filing_fetched", "coverage_pct": 10},
                {"id": "fair_band_present", "coverage_pct": 55},
                {"id": "stance_analyzed", "coverage_pct": 20},
            ]
        }
        assert check(ok_report, thresholds) == []
        assert check(bad_report, thresholds)
        print(json.dumps({"self_test": "ok", "n_domains": len(thresholds["domains"])}))
        return 0

    if len(sys.argv) < 2:
        print("usage: check_coverage_thresholds.py <coverage_report.json>|--self-test", file=sys.stderr)
        return 2
    report = json.loads(Path(sys.argv[1]).read_text())
    errors = check(report, thresholds)
    if errors:
        print("coverage floor failures:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "n_domains": len(thresholds["domains"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
