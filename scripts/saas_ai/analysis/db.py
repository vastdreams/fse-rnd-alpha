"""Small asyncpg-to-pandas helpers for reproducible research scripts."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import asyncpg
import pandas as pd


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL not set.")
    return url.replace("+asyncpg", "")


async def _fetch(query: str, args: tuple) -> pd.DataFrame:
    conn = await asyncpg.connect(_dsn())
    try:
        rows = await conn.fetch(query, *args)
    finally:
        await conn.close()
    return pd.DataFrame([dict(row) for row in rows])


def read_df(query: str, *args) -> pd.DataFrame:
    return asyncio.run(_fetch(query, args))


def read_universe() -> list[str]:
    root = Path(__file__).resolve().parents[3]
    path = root / "config" / "saas_ai_universe.txt"
    symbols = [
        line.strip().upper()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return sorted(set(symbols))
