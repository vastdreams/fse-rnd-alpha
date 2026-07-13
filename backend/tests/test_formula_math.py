"""
PATH: backend/tests/test_formula_math.py
PURPOSE: Prove shared formula_math + registry IDs (finance-safe references).
"""

from pathlib import Path

from app.contracts.formula_registry import audited_formula_ids, formula_ids, load_formula_registry
from app.services.formula_math import (
    MAD_SIGMA,
    R3_AXIS_WEIGHTS,
    ROBUST_Z_WINSOR,
    annualized_from_gap,
    annualized_from_prices,
    hold_horizon_years,
    live_gap_pct,
    mos_equals_live_gap,
    mos_from_price_target,
)
from app.services.rank_service.engine import WINSOR_LIMIT, _MAD_SIGMA, _PRESET_AXES


def test_mos_live_gap_identity():
    assert mos_equals_live_gap(89.67, 249.77850114953984)
    assert abs(mos_from_price_target(100, 150) - 0.5) < 1e-12
    assert abs(live_gap_pct(100, 150) - 0.5) < 1e-12


def test_annualized_price_and_gap_agree():
    # gap = 0.5 over 2y via prices 100→150
    a = annualized_from_prices(100, 150, 2)
    b = annualized_from_gap(0.5, 2)
    assert a is not None and b is not None
    assert abs(a - b) < 1e-12


def test_hold_horizon_buckets():
    assert hold_horizon_years(None) is None
    assert hold_horizon_years(0) is None
    assert hold_horizon_years(0.1) == 1
    assert hold_horizon_years(0.25) == 2
    assert hold_horizon_years(0.6) == 3


def test_robust_z_constants_match_engine():
    assert MAD_SIGMA == _MAD_SIGMA == 1.4826
    assert ROBUST_Z_WINSOR == WINSOR_LIMIT == 3.0


def test_r3_weights_match_engine():
    axes = _PRESET_AXES["R3"]
    got = {a.name: a.weight for a in axes}
    assert got == R3_AXIS_WEIGHTS


def test_formula_registry_loads_and_audited_paths_exist():
    reg = load_formula_registry()
    assert reg["schema_version"] == 1
    ids = formula_ids()
    assert "F_VS_MEDIAN_PCT" in ids
    assert "F_SELL_CEILING" in ids
    assert "F_SCORE_ROBUST_Z" in ids
    repo = Path(__file__).resolve().parents[2]  # backend/ → repo when tests live in backend/tests
    if not (repo / "contracts" / "formula-registry.json").is_file():
        repo = Path(__file__).resolve().parents[1]
    for fid in audited_formula_ids():
        row = next(f for f in reg["formulas"] if f["id"] == fid)
        assert row.get("expression"), fid
        assert row.get("reference", {}).get("cite"), fid
        found = any((repo / rel).is_file() for rel in row.get("audit") or [])
        assert found, f"{fid} has no existing audit file among {row.get('audit')} (repo={repo})"
