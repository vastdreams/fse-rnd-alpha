"""
PATH: backend/tests/test_recipe_engine_parity.py
PURPOSE: Investor-facing recipe copy must match the rank engine (no marketing lies).
"""

from app.contracts.recipes import PRESET_RECIPES
from app.services.formula_math import R3_AXIS_WEIGHTS
from app.services.rank_service.engine import _PRESET_AXES, _PRESET_FILTERS


def test_every_preset_axes_match_engine():
    for recipe in PRESET_RECIPES:
        engine_axes = [a.name for a in _PRESET_AXES[recipe.recipe_id]]
        assert recipe.axes == engine_axes, recipe.recipe_id
        assert "1.4826" in recipe.formula_exact or recipe.recipe_id == "R2"
        # R2 hard-filter text may lead; still must describe MAD z for scoring
        assert "winsor" in recipe.formula_exact.lower() or "1.4826" in recipe.formula_exact
        assert recipe.recipe_id in _PRESET_FILTERS


def test_r3_weights_match_engine():
    assert {a.name: a.weight for a in _PRESET_AXES["R3"]} == R3_AXIS_WEIGHTS


def test_r2_weights():
    assert {a.name: a.weight for a in _PRESET_AXES["R2"]} == {"mos_live": 2.0, "rd_prod": 1.0}


def test_no_marketing_only_axes():
    banned = {"cohort", "table20_pass_count", "gm"}  # gm banned only where not an engine axis
    for recipe in PRESET_RECIPES:
        engine = {a.name for a in _PRESET_AXES[recipe.recipe_id]}
        for axis in recipe.axes:
            assert axis in engine, (recipe.recipe_id, axis)
        # cohort must never appear
        assert "cohort" not in recipe.axes
        assert "table20_pass_count" not in recipe.axes
