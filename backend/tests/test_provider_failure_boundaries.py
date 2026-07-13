"""Provider outages must become explicit unavailable/unknown states, never 500s."""

from datetime import datetime, timedelta, timezone
import json

import aiohttp
import pytest

import app.services.company_meta_service as company_meta_service
import app.services.financials_service as financials_service
import app.services.price_history_service as price_history_service


class _UnavailableSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def get(self, *_args, **_kwargs):
        raise aiohttp.ClientConnectionError("provider unavailable")


@pytest.mark.asyncio
async def test_price_history_translates_provider_connection_failure(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(price_history_service.settings, "NASDAQ_DATA_LINK_API_KEY", "test-key")
    monkeypatch.setattr(price_history_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(price_history_service, "DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(price_history_service.aiohttp, "ClientSession", _UnavailableSession)
    price_history_service._memory.clear()

    with pytest.raises(price_history_service.PriceHistoryUnavailable, match="temporarily unavailable"):
        await price_history_service.get_price_history("ACME")


@pytest.mark.asyncio
async def test_financials_translates_provider_connection_failure(monkeypatch) -> None:
    with pytest.raises(financials_service.FinancialsUnavailable, match="temporarily unavailable"):
        await financials_service._fetch_sf1(_UnavailableSession(), "ACME", "MRY")


@pytest.mark.asyncio
async def test_stale_price_cache_survives_provider_outage(monkeypatch, tmp_path) -> None:
    stale_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    (tmp_path / "ACME_1095.json").write_text(
        json.dumps(
            {
                "ticker": "ACME",
                "fetched_at": stale_at,
                "end": "2026-07-01",
                "bars": [{"date": "2026-07-01", "close": 10.0}],
            }
        )
    )
    monkeypatch.setattr(price_history_service.settings, "NASDAQ_DATA_LINK_API_KEY", "test-key")
    monkeypatch.setattr(price_history_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(price_history_service, "DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(price_history_service.aiohttp, "ClientSession", _UnavailableSession)
    price_history_service._memory.clear()

    history = await price_history_service.get_price_history("ACME")

    assert history["cache_stale"] is True
    assert history["bars"][-1]["close"] == 10.0


@pytest.mark.asyncio
async def test_stale_financial_cache_survives_provider_outage(monkeypatch, tmp_path) -> None:
    stale_at = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    (tmp_path / "ACME.json").write_text(
        json.dumps({"ticker": "ACME", "fetched_at": stale_at, "annual": [], "quarterly": []})
    )
    monkeypatch.setattr(financials_service.settings, "NASDAQ_DATA_LINK_API_KEY", "test-key")
    monkeypatch.setattr(financials_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(financials_service, "DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(financials_service.aiohttp, "ClientSession", _UnavailableSession)
    financials_service._memory_cache.clear()

    financials = await financials_service.get_financials("ACME")

    assert financials["cache_stale"] is True
    assert financials["ticker"] == "ACME"


@pytest.mark.asyncio
async def test_identity_overlay_degrades_to_unknown_when_provider_is_down(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(company_meta_service.settings, "NASDAQ_DATA_LINK_API_KEY", "test-key")
    monkeypatch.setattr(company_meta_service, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(company_meta_service, "DEFAULT_CACHE_DIR", tmp_path)
    monkeypatch.setattr(company_meta_service, "_identity_cache", None)
    monkeypatch.setattr(company_meta_service, "_identity_loaded_at", 0.0)
    monkeypatch.setattr(company_meta_service.aiohttp, "ClientSession", _UnavailableSession)

    assert await company_meta_service.identity_map(["ACME"]) == {"ACME": {}}
