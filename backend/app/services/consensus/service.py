"""
PATH: backend/app/services/consensus/service.py
PURPOSE: Fetch licensed consensus, store an immutable PIT snapshot row, and
serve the latest stored snapshot to the report builder.

The report builder never calls a vendor directly: it only reads rows that
were already sealed into consensus_snapshots with a payload hash.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.consensus.base import (
    ConsensusEstimate,
    ConsensusProvider,
    ConsensusUnavailable,
    NormalizedConsensus,
    PriceTargetSummary,
)
from app.services.consensus.fmp_provider import FmpConsensusProvider

_DEFAULT_PROVIDER: ConsensusProvider = FmpConsensusProvider()


def _payload_sha256(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _consensus_id(ticker: str, provider: str, sha: str, fetched_at: datetime) -> str:
    seed = f"{ticker}|{provider}|{sha}|{fetched_at.isoformat()}"
    return "cons_" + hashlib.sha256(seed.encode()).hexdigest()[:24]


async def fetch_and_store_consensus(
    db: AsyncSession,
    ticker: str,
    provider: Optional[ConsensusProvider] = None,
) -> NormalizedConsensus:
    """Pull the vendor payload now and seal it as an append-only PIT row."""
    adapter = provider or _DEFAULT_PROVIDER
    ticker = ticker.upper()
    raw = await adapter.fetch_raw(ticker)  # raises ConsensusUnavailable
    estimates, price_targets = adapter.normalize(ticker, raw)
    if not estimates and price_targets is None:
        raise ConsensusUnavailable(f"No usable consensus rows for {ticker}")

    fetched_at = datetime.now(timezone.utc).replace(tzinfo=None)
    today = fetched_at.date()
    sha = _payload_sha256(raw)
    consensus_id = _consensus_id(ticker, adapter.name, sha, fetched_at)
    normalized = NormalizedConsensus(
        ticker=ticker,
        provider=adapter.name,
        consensus_id=consensus_id,
        # A live consensus pull describes and becomes knowable on fetch day.
        as_of_date=today,
        available_date=today,
        payload_sha256=sha,
        estimates=estimates,
        price_targets=price_targets,
    )
    await db.execute(
        text(
            """INSERT INTO consensus_snapshots
                   (consensus_id, ticker, provider, kind, payload, payload_sha256,
                    as_of_date, available_date, fetched_at)
               VALUES (:cid, :t, :p, 'consensus_bundle', CAST(:payload AS jsonb), :sha,
                       :asof, :avail, :fetched)"""
        ),
        {
            "cid": consensus_id,
            "t": ticker,
            "p": adapter.name,
            "payload": json.dumps(
                {
                    "raw": raw,
                    "normalized": normalized.model_dump(mode="json"),
                },
                default=str,
            ),
            "sha": sha,
            "asof": today,
            "avail": today,
            "fetched": fetched_at,
        },
    )
    await db.commit()
    return normalized


async def latest_stored_consensus(
    db: AsyncSession,
    ticker: str,
    *,
    on_or_before: Optional[date] = None,
) -> Optional[NormalizedConsensus]:
    """Latest sealed consensus row for a ticker, honouring a PIT cutoff."""
    row = (
        await db.execute(
            text(
                """SELECT payload
                     FROM consensus_snapshots
                    WHERE ticker = :t
                      AND kind = 'consensus_bundle'
                      AND (CAST(:cutoff AS date) IS NULL OR available_date <= CAST(:cutoff AS date))
                    ORDER BY as_of_date DESC, fetched_at DESC
                    LIMIT 1"""
            ),
            {"t": ticker.upper(), "cutoff": on_or_before},
        )
    ).first()
    if row is None:
        return None
    payload = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    normalized = payload.get("normalized")
    if not isinstance(normalized, dict):
        return None
    return NormalizedConsensus.model_validate(normalized)


__all__ = [
    "ConsensusEstimate",
    "ConsensusUnavailable",
    "NormalizedConsensus",
    "PriceTargetSummary",
    "fetch_and_store_consensus",
    "latest_stored_consensus",
]
