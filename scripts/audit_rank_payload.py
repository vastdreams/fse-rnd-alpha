#!/usr/bin/env python3
"""
PATH: scripts/audit_rank_payload.py
PURPOSE: S3 staging smoke — audit a rank API JSON payload; exit 1 on violations.

Usage:
  python scripts/audit_rank_payload.py path/to/rank.json
  curl -sS .../api/universe/rank?mode=buy | python scripts/audit_rank_payload.py -
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from repo root without installing the package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.rank_row_invariants import audit_rank_rows  # noqa: E402


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else "-"
    raw = sys.stdin.read() if src == "-" else Path(src).read_text()
    payload = json.loads(raw)
    rows = payload.get("rows") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        print("expected {rows:[...]} or a list", file=sys.stderr)
        return 2
    violations = audit_rank_rows(rows)
    meta = payload.get("meta") if isinstance(payload, dict) else {}
    report = {
        "n_rows": len(rows),
        "n_violations": len(violations),
        "universe_version": (meta or {}).get("universe_version")
        or (rows[0].get("universe_version") if rows else None),
        "violations": violations,
    }
    print(json.dumps(report, indent=2))
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
