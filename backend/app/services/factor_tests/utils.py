"""
PATH: backend/app/services/factor_tests/utils.py
PURPOSE: Shared utility functions for factor test modules
WHY: Avoids duplication of safe_qcut across mispricing and liquidity modules
"""

import pandas as pd


def safe_qcut(series: "pd.Series", q: int, labels: list) -> "pd.Series":
    """
    Robust qcut with fallback when there are too few unique values.

    Uses rank(method="first") to break ties, then falls back to pd.cut
    if pd.qcut still raises ValueError.
    """
    ranked = series.rank(method="first")
    try:
        return pd.qcut(ranked, q, labels=labels)
    except ValueError:
        return pd.cut(ranked, q, labels=labels)
