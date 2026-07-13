"""Frozen panel DCF seeds must preserve unknowns rather than invent inputs."""

from app.api.routes.universe_company import _frozen_dcf_seed


def test_frozen_dcf_seed_uses_only_panel_values_and_labels_unknowns() -> None:
    seed = _frozen_dcf_seed(
        "seed",
        {
            "revenue_usd": 1_000_000,
            "fcf_usd": 100_000,
            "fcfm_sbc": 0.1,
            "net_cash_usd": 50_000,
            "ev_mult_usd": 1_500_000,
            "price_snapshot": 12.5,
            "rev_cagr": 0.5,
            "wacc": 0.11,
            "fundamentals_as_of": "2026-06-30",
        },
    )

    assert seed is not None
    assert seed["inputs"]["ticker"] == "SEED"
    assert seed["inputs"]["growth"] == 0.30
    assert seed["inputs"]["revenue_usd"] == 1_000_000
    assert seed["inputs"]["shares_fut_implied"] is None
    assert seed["missing_inputs"] == ["shares_fut_implied"]
    assert seed["as_of"] == "2026-06-30"


def test_frozen_dcf_seed_requires_reported_growth_and_wacc() -> None:
    assert _frozen_dcf_seed("seed", {"revenue_usd": 1_000_000}) is None
