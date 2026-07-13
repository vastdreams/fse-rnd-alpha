"""
PATH: backend/tests/test_recipes_lit.py
PURPOSE: Golden test — every preset recipe axis must carry a literature bind,
and preset formulas must be present (shown on screen is a ship rule).
"""

from app.contracts.recipes import LITERATURE_BINDS, PRESET_RECIPES, unbound_axes


def test_every_preset_axis_has_literature_bind():
    missing = unbound_axes()
    assert missing == [], f"Axes without literature binds cannot ship in recipes: {missing}"


def test_all_eight_presets_defined():
    ids = [r.recipe_id for r in PRESET_RECIPES]
    assert ids == ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8"]


def test_presets_have_formulas_and_benchmarks():
    for r in PRESET_RECIPES:
        assert r.formula_human.strip(), f"{r.recipe_id} missing human formula"
        assert r.formula_exact.strip(), f"{r.recipe_id} missing exact formula"
        assert r.benchmark_vs.strip(), f"{r.recipe_id} missing benchmark"
        assert r.custom is False


def test_binds_have_citations():
    for b in LITERATURE_BINDS:
        assert b.citation.strip()
        assert b.bib_key.strip()
