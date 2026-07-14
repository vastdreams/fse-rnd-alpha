"""
PATH: backend/app/contracts/decision_chains.py
PURPOSE: Load contracts/decision-chains.json — data-driven gate provenance.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.contracts.paths import contracts_dir


@lru_cache(maxsize=1)
def load_decision_chains() -> dict[str, Any]:
    path = contracts_dir() / "decision-chains.json"
    return json.loads(path.read_text(encoding="utf-8"))


def chain_by_id(chain_id: str) -> dict[str, Any]:
    for row in load_decision_chains()["chains"]:
        if row["id"] == chain_id:
            return row
    raise KeyError(chain_id)


def chain_ids() -> list[str]:
    return [c["id"] for c in load_decision_chains()["chains"]]


def hard_steps(chain_id: str) -> list[dict[str, Any]]:
    return [s for s in chain_by_id(chain_id)["steps"] if s.get("gate_kind") == "hard"]


def assert_no_opinion_hard_gates(chain_id: str) -> None:
    """Fail closed if any hard step is marked opinion=true."""
    for step in hard_steps(chain_id):
        if step.get("opinion") is True:
            raise AssertionError(f"{chain_id}.{step.get('id')} hard gate marked opinion=true")
