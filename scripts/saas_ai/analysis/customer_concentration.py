"""Extract only explicitly disclosed customer-concentration percentages."""

from __future__ import annotations

import re
from typing import Any


_CONCENTRATION_PATTERNS = [
    r"(top 10 customers[^.]{0,120}?(?:accounted for|represented|comprised)[^.]{0,80}?([0-9]{1,2})\s*%)",
    r"((?:largest|individual) customers?[^.]{0,120}?(?:accounted for|represented|comprised)[^.]{0,80}?([0-9]{1,2})\s*%)",
    r"(no individual customer[^.]{0,120}?accounted for[^.]{0,80}?(?:more than\s+)?([0-9]{1,2})\s*%)",
    r"(our largest customer[^.]{0,120}?(?:accounted for|represented)[^.]{0,80}?([0-9]{1,2})\s*%)",
    r"(customer concentration[^.]{0,120}?([0-9]{1,2})\s*%)",
]
_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in _CONCENTRATION_PATTERNS]


def extract_customer_concentration(filing_text: str | None) -> dict[str, Any]:
    if not filing_text:
        return {
            "top10_pct": None,
            "raw_value": None,
            "raw_match": None,
            "source": "not found",
        }

    for pattern in _COMPILED:
        match = pattern.search(filing_text)
        if match:
            pct = int(match.group(2))
            return {
                "top10_pct": round(pct / 100.0, 4),
                "raw_value": f"{pct}%",
                "raw_match": match.group(1),
                "source": "10-K Risk Factors or MD&A",
            }

    return {
        "top10_pct": None,
        "raw_value": None,
        "raw_match": None,
        "source": "not found",
    }
