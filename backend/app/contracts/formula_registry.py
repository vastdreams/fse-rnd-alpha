"""
PATH: backend/app/contracts/formula_registry.py
PURPOSE: Load contracts/formula-registry.json — provenance for every investor number.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.contracts.paths import contracts_dir


@lru_cache(maxsize=1)
def load_formula_registry() -> dict[str, Any]:
    path = contracts_dir() / "formula-registry.json"
    return json.loads(path.read_text(encoding="utf-8"))


def formula_ids() -> list[str]:
    return [f["id"] for f in load_formula_registry()["formulas"]]


def formula_by_id(formula_id: str) -> dict[str, Any]:
    for row in load_formula_registry()["formulas"]:
        if row["id"] == formula_id:
            return row
    raise KeyError(formula_id)


def audited_formula_ids() -> list[str]:
    return [f["id"] for f in load_formula_registry()["formulas"] if f.get("status") == "audited"]
