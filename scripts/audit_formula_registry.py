#!/usr/bin/env python3
"""
PATH: scripts/audit_formula_registry.py
PURPOSE: Fail-closed check that contracts/formula-registry.json is coherent
         and every audited formula cites an existing audit file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "contracts" / "formula-registry.json"
FE_COPY = ROOT / "frontend" / "src" / "fixtures" / "formula-registry.json"


def main() -> int:
    if not REG.is_file():
        print(f"missing {REG}", file=sys.stderr)
        return 1
    raw = REG.read_bytes()
    if not FE_COPY.is_file() or FE_COPY.read_bytes() != raw:
        print("FE fixture must be an exact byte copy of contracts/formula-registry.json", file=sys.stderr)
        return 1
    reg = json.loads(raw.decode("utf-8"))
    assert reg["schema_version"] == 1
    ids = [f["id"] for f in reg["formulas"]]
    if len(ids) != len(set(ids)):
        print("duplicate formula ids", file=sys.stderr)
        return 1
    missing = []
    for row in reg["formulas"]:
        if row.get("status") != "audited":
            continue
        ok = any((ROOT / rel).is_file() for rel in row.get("audit") or [])
        if not ok:
            missing.append(row["id"])
    if missing:
        print("audited formulas missing audit files:", ", ".join(missing), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "n_formulas": len(ids),
                "n_audited": sum(1 for f in reg["formulas"] if f.get("status") == "audited"),
                "n_documented": sum(1 for f in reg["formulas"] if f.get("status") == "documented"),
                "ok": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
