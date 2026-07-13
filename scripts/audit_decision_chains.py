#!/usr/bin/env python3
"""
PATH: scripts/audit_decision_chains.py
PURPOSE: Fail-closed audit of decision-chains.json — no opinion hard gates;
         every formula_id must exist in formula-registry.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAINS = ROOT / "contracts" / "decision-chains.json"
FORMULAS = ROOT / "contracts" / "formula-registry.json"
FE_COPY = ROOT / "frontend" / "src" / "fixtures" / "decision-chains.json"


def main() -> int:
    if not CHAINS.is_file():
        print(f"missing {CHAINS}", file=sys.stderr)
        return 1
    raw = CHAINS.read_bytes()
    if not FE_COPY.is_file() or FE_COPY.read_bytes() != raw:
        print("FE fixture must be an exact byte copy of contracts/decision-chains.json", file=sys.stderr)
        return 1
    chains = json.loads(raw.decode("utf-8"))
    formulas = {f["id"] for f in json.loads(FORMULAS.read_text())["formulas"]}
    assert chains["schema_version"] == 1
    errors: list[str] = []
    for chain in chains["chains"]:
        for step in chain.get("steps") or []:
            if step.get("gate_kind") == "hard" and step.get("opinion") is True:
                errors.append(f"{chain['id']}.{step['id']}: hard gate marked opinion=true")
            if not step.get("data_fields"):
                errors.append(f"{chain['id']}.{step['id']}: hard/derived step missing data_fields")
            for fid in step.get("formula_ids") or []:
                if fid not in formulas:
                    errors.append(f"{chain['id']}.{step['id']}: unknown formula_id {fid}")
            if step.get("gate_kind") == "hard" and not step.get("on_unknown"):
                errors.append(f"{chain['id']}.{step['id']}: hard gate missing on_unknown policy")
        for adv in chain.get("advisory_not_gates") or []:
            if adv.get("gate_kind") != "advisory":
                errors.append(f"{chain['id']}.{adv.get('id')}: advisory_not_gates must be advisory")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        json.dumps(
            {
                "n_chains": len(chains["chains"]),
                "chain_ids": [c["id"] for c in chains["chains"]],
                "ok": True,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
