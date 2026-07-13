"""
PATH: backend/tests/test_recipe_engine_parity.py
PURPOSE: Investor-facing recipe copy must match the rank engine (no marketing lies).
"""

from app.contracts.recipes import PRESET_RECIPES
from app.services.formula_math import R3_AXIS_WEIGHTS
from app.services.rank_service.engine import _PRESET_AXES, _PRESET_FILTERS


def test_r3_axes_and_weights_match_engine():
    r3 = next(r for r in PRESET_RECIPES if r.recipe_id == "R3")
    engine_axes = [a.name for a in _PRESET_AXES["R3"]]
    assert r3.axes == engine_axes
    assert {a.name: a.weight for a in _PRESET_AXES["R3"]} == R3_AXIS_WEIGHTS
    assert "1.4826" in r3.formula_exact
    assert "winsor" in r3.formula_exact.lower() or "±3" in r3.formula_exact
    assert r3.hard_filters == ["kill_active == False", "carve_out == False"]
    assert "R3" in _PRESET_FILTERS


def test_every_engine_recipe_has_preset():
    preset_ids = {r.recipe_id for r in PRESET_RECIPES}
    for rid in _PRESET_AXES:
        assert rid in preset_ids, rid
