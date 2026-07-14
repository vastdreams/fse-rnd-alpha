"""Tests for the market-implied repricing break-even p* (display only)."""

from __future__ import annotations

import pytest

from app.services.reprice_break_even import p_star, p_star_payload


def test_p_star_happy_path():
    assert p_star(price=12.0, v_base_med=10.0, v_rep_med=20.0) == pytest.approx(0.2)


def test_p_star_free_option_when_price_below_base():
    value = p_star(price=8.0, v_base_med=10.0, v_rep_med=20.0)
    assert value == pytest.approx(-0.2)
    payload = p_star_payload(8.0, 10.0, 20.0)
    assert "free option" in payload["reading"]


def test_p_star_over_paid_reading():
    payload = p_star_payload(25.0, 10.0, 20.0)
    assert payload["p_star"] == pytest.approx(1.5)
    assert "over-paid" in payload["reading"]


def test_p_star_degenerate_and_missing_inputs():
    assert p_star(price=12.0, v_base_med=10.0, v_rep_med=10.0) is None  # rep == base
    assert p_star(price=12.0, v_base_med=10.0, v_rep_med=5.0) is None  # rep < base
    assert p_star(price=None, v_base_med=10.0, v_rep_med=20.0) is None
    assert p_star(price=-5.0, v_base_med=10.0, v_rep_med=20.0) is None
    payload = p_star_payload(12.0, None, 20.0)
    assert payload["p_star"] is None
    assert "No repricing leg" in payload["reading"]


def test_p_star_never_gates_flag():
    assert p_star_payload(12.0, 10.0, 20.0)["never_gates"] is True
