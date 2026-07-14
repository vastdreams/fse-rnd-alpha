"""
PATH: backend/tests/test_decision_chains.py
PURPOSE: Decision-chain registry integrity + stance flowchart provenance.
"""

from app.contracts.decision_chains import (
    assert_no_opinion_hard_gates,
    chain_by_id,
    chain_ids,
    load_decision_chains,
)
from app.contracts.formula_registry import formula_ids
from app.services.decision_provenance import (
    enrich_flowchart_node,
    rank_row_provenance,
    stance_decision_provenance,
)


def test_decision_chains_load():
    reg = load_decision_chains()
    assert reg["schema_version"] == 1
    assert "D_STANCE_BUY" in chain_ids()
    assert "D_RANK_R3" in chain_ids()
    assert_no_opinion_hard_gates("D_STANCE_BUY")
    assert_no_opinion_hard_gates("D_RANK_R3")


def test_contracts_dir_resolves_sealed_json():
    """Rank enrichment 500s if contracts are missing from the runtime image."""
    from app.contracts.paths import contracts_dir

    root = contracts_dir()
    assert (root / "decision-chains.json").is_file()
    assert (root / "formula-registry.json").is_file()
    # Provenance path used by every /api/universe/rank row.
    assert rank_row_provenance({"ticker": "TEST"})["decision_chain_id"] == "D_RANK_R3"


def test_formula_ids_in_chains_exist():
    known = set(formula_ids())
    for chain in load_decision_chains()["chains"]:
        for step in chain["steps"]:
            for fid in step.get("formula_ids") or []:
                assert fid in known, (chain["id"], step["id"], fid)


def test_p2_fcf_is_advisory_not_hard_buy_gate():
    buy = chain_by_id("D_STANCE_BUY")
    hard_ids = {s["id"] for s in buy["steps"] if s["gate_kind"] == "hard"}
    assert "P2_FCF" not in hard_ids
    adv = next(a for a in buy["advisory_not_gates"] if a["id"] == "P2_FCF")
    assert adv["gate_kind"] == "advisory"


def test_rank_row_provenance_is_assumption_free():
    p = rank_row_provenance(
        {"price_live": 500.0, "fair_px_hi": 100.0, "ticker": "APP"}
    )
    assert p["decision_chain_id"] == "D_RANK_R3"
    assert p["assumption_policy"] == "no_imputation"
    assert p["above_band_advisory"] is True
    assert "F_VS_MEDIAN_PCT" in p["formula_ids"]


def test_flowchart_enrichment_carries_references():
    node = enrich_flowchart_node(
        {"id": "F3", "label": "MoS", "result": "PASS", "detail": "ok"},
        formula_ids=["F_MOS_LIVE"],
        data_fields=["mos_live"],
    )
    assert node["opinion"] is False
    assert node["gate_kind"] == "hard"
    assert node["formula_ids"] == ["F_MOS_LIVE"]
    assert node["references"]


def test_stance_decision_provenance_blob():
    blob = stance_decision_provenance()
    assert blob["decision_chain_id"] == "D_STANCE_BUY"
    assert "F1" in blob["hard_gate_ids"]


def test_f3b_live_vs_sealed_is_hard_gate():
    buy = chain_by_id("D_STANCE_BUY")
    step = next(s for s in buy["steps"] if s["id"] == "F3b")
    assert step["gate_kind"] == "hard"
    assert "F_LIVE_VS_SEALED_GATE" in step["formula_ids"]


def test_thesis_gates_are_hard_and_ordered():
    """close_call_v3 thesis gates: F0 RD spine, F2b survivability, F3c skew."""
    buy = chain_by_id("D_STANCE_BUY")
    ids = [s["id"] for s in buy["steps"]]
    assert ids == ["F0", "F1", "F2", "F2b", "F3", "F3b", "F3c", "F4", "F5", "F6"]
    for sid, fid in (("F0", "F_RD_COMPOSITE"), ("F2b", "F_SURVIVABILITY_FLOORS"), ("F3c", "F_PAYOFF_SKEW")):
        step = next(s for s in buy["steps"] if s["id"] == sid)
        assert step["gate_kind"] == "hard"
        assert step["on_unknown"] == "block_buy"
        assert fid in step["formula_ids"]
