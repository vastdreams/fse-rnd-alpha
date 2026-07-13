"""Extract explicit AI-related risk language from filing text."""

from __future__ import annotations

import re
from typing import Any


_AI_RE = re.compile(
    r"generative ai|large language model|large language models|llm|llms|"
    r"generative artificial intelligence|\bartificial intelligence\b|\bAI\b",
    re.IGNORECASE,
)
_RISK_RE = re.compile(
    r"adversely affect|adverse impacts?|negative consequences|reputational harm|"
    r"competitive harm|legal liability|regulatory liability|operational challenges|"
    r"range of risks associated|risks associated with|substitut|replace|disrupt|"
    r"reduce demand|commodit|failure to|unable to|may not|could harm",
    re.IGNORECASE,
)


def extract_ai_risk_flags(
    ticker: str, fiscal_year: int, filing_text: str | None = None
) -> dict[str, Any]:
    if not filing_text:
        return {
            "ticker": ticker,
            "fiscal_year": fiscal_year,
            "has_ai_risk": False,
            "ai_risk_sentences": [],
            "source": "EDGAR 10-K Item 1A",
            "filing_date": "unknown",
            "note": "filing_text not provided - production fetch not wired",
        }

    matches = [
        sentence.strip()
        for sentence in _split_into_sentences(filing_text)
        if _AI_RE.search(sentence) and _RISK_RE.search(sentence)
    ]
    return {
        "ticker": ticker,
        "fiscal_year": fiscal_year,
        "has_ai_risk": bool(matches),
        "ai_risk_sentences": matches,
        "source": "EDGAR 10-K Item 1A",
        "filing_date": "unknown",
    }


def _split_into_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?;])\s+|•", text)
    return [part.strip() for part in parts if len(part.strip()) > 20]
