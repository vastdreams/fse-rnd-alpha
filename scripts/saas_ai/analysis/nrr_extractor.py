"""Extract only explicitly disclosed net-revenue-retention percentages."""

from __future__ import annotations

import re
from typing import Any


_PCT = r"(?P<pct>[0-9]{2,3})\s*%"
_MOD = r"(?P<mod>greater than|approximately|about|over|at least)?"
_KW = (
    r"(?:net\s+revenue\s+retention(?:\s+rate)?"
    r"|net\s+dollar\s+retention(?:\s+rate)?"
    r"|dollar[- ]based\s+net\s+retention(?:\s+rate)?"
    r"|subscription\s+(?:dollar[- ]based\s+)?(?:net\s+)?retention(?:\s+rate)?"
    r"|revenue\s+retention\s+rate"
    r"|net\s+dollar[- ]based\s+retention(?:\s+rate)?"
    r"|recurring\s+revenue\s+dollar[- ]based\s+net\s+retention(?:\s+rate)?"
    r"|\bNRR\b|\bNDR\b)"
)
_NRR_PATTERNS = [
    rf"({_KW}[^.]{{0,160}}?{_MOD}\s*{_PCT})",
    rf"({_MOD}\s*{_PCT}[^.]{{0,80}}?{_KW})",
    rf"({_KW}\s+{_PCT})",
]
_COMPILED = [re.compile(pattern, re.IGNORECASE | re.DOTALL) for pattern in _NRR_PATTERNS]


def extract_nrr(filing_text: str | None) -> dict[str, Any]:
    if not filing_text:
        return {
            "nrr": None,
            "raw_value": None,
            "raw_match": None,
            "operator": None,
            "source": "not found",
        }

    for pattern in _COMPILED:
        match = pattern.search(filing_text)
        if not match:
            continue
        pct = int(match.group("pct"))
        if pct < 50 or pct > 250:
            continue
        modifier = (match.groupdict().get("mod") or "").lower()
        operator = (
            ">"
            if modifier in {"greater than", "over", "at least"}
            else "~"
            if modifier in {"approximately", "about"}
            else "="
        )
        raw = re.sub(r"\s+", " ", match.group(1)).strip()
        return {
            "nrr": round(pct / 100.0, 4),
            "raw_value": f"{pct}%",
            "raw_match": raw[:500],
            "operator": operator,
            "source": "10-K MD&A or footnotes",
        }

    return {
        "nrr": None,
        "raw_value": None,
        "raw_match": None,
        "operator": None,
        "source": "not found",
    }
