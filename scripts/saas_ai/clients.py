"""Async API clients used by reproducible SaaS research backfills."""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from typing import Any, AsyncIterator, Optional

import httpx


logger = logging.getLogger("saas_ai.clients")
AV_BASE = "https://www.alphavantage.co/query"
ND_BASE = "https://data.nasdaq.com/api/v3/datatables"


class AlphaVantageClient:
    def __init__(
        self,
        api_key: str,
        calls_per_min: int = 75,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.delay = 60.0 / max(calls_per_min, 1)
        self._client = client
        self._owns = client is None

    async def __aenter__(self) -> "AlphaVantageClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=60)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._owns and self._client:
            await self._client.aclose()

    async def _get(self, params: dict) -> Any:
        params = dict(params)
        params["apikey"] = self.api_key
        await asyncio.sleep(self.delay)
        response = await self._client.get(AV_BASE, params=params)
        response.raise_for_status()
        if "json" in response.headers.get("content-type", ""):
            data = response.json()
            if isinstance(data, dict) and ("Note" in data or "Information" in data):
                logger.warning(
                    "AV throttle/info: %s",
                    str(data.get("Note") or data.get("Information"))[:160],
                )
            return data
        return response.text

    async def transcript(self, symbol: str, quarter: str) -> Any:
        return await self._get(
            {"function": "EARNINGS_CALL_TRANSCRIPT", "symbol": symbol, "quarter": quarter}
        )

    async def fundamental(self, symbol: str, function: str) -> Any:
        return await self._get({"function": function, "symbol": symbol})

    async def listing_status(self, state: str = "active") -> list[dict]:
        text = await self._get({"function": "LISTING_STATUS", "state": state})
        return list(csv.DictReader(io.StringIO(text))) if isinstance(text, str) else []


class SharadarClient:
    def __init__(
        self,
        api_key: str,
        client: Optional[httpx.AsyncClient] = None,
        page_pause: float = 0.2,
    ):
        self.api_key = api_key
        self._client = client
        self._owns = client is None
        self.page_pause = page_pause

    async def __aenter__(self) -> "SharadarClient":
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        if self._owns and self._client:
            await self._client.aclose()

    async def datatable(self, table: str, **filters: Any) -> AsyncIterator[dict]:
        base_params = {key: value for key, value in filters.items() if value is not None}
        base_params["api_key"] = self.api_key
        url = f"{ND_BASE}/SHARADAR/{table}.json"
        cursor: Optional[str] = None
        while True:
            params = dict(base_params)
            if cursor:
                params["qopts.cursor_id"] = cursor
            response = await self._client.get(url, params=params)
            if response.status_code == 429:
                logger.warning("Sharadar rate limited; backing off 2s")
                await asyncio.sleep(2)
                continue
            response.raise_for_status()
            payload = response.json()
            datatable = payload.get("datatable", {})
            columns = [column["name"] for column in datatable.get("columns", [])]
            for row in datatable.get("data", []):
                yield dict(zip(columns, row))
            cursor = payload.get("meta", {}).get("next_cursor_id")
            if not cursor:
                break
            await asyncio.sleep(self.page_pause)
