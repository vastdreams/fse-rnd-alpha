"""PATH: backend/tests/test_tradability.py — ADV / capacity helpers."""

from app.services.tradability import adv_usd_from_bars, capacity_note


def test_adv_usd_happy_path():
    bars = [{"close": 10.0, "volume": 1000} for _ in range(20)]
    assert adv_usd_from_bars(bars) == 10_000.0


def test_adv_usd_unknown_when_volume_missing():
    bars = [{"close": 10.0, "volume": None} for _ in range(20)]
    assert adv_usd_from_bars(bars) is None


def test_capacity_note_unknown():
    assert "unknown" in capacity_note(None).lower()
