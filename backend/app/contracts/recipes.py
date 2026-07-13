"""
PATH: backend/app/contracts/recipes.py
PURPOSE: Canonical R1–R8 recipe definitions + literature binds (W1).

R9 (custom builder) is created at runtime from user selections and saved to
rank_recipes with custom=True; it is not defined here.

HARD RULE (tested in test_contracts_golden.py / test_recipes_lit.py):
every axis consumed by a preset recipe MUST have a LiteratureBind here.
An axis without a bind cannot ship in a recipe.
"""

from __future__ import annotations

from app.contracts.research import LiteratureBind, RankRecipe

# =============================================================================
# Literature binds — every rank-moving axis
# =============================================================================

LITERATURE_BINDS: list[LiteratureBind] = [
    # R&D Alpha constructs (Paper-1)
    LiteratureBind(
        axis="rd_int",
        bib_key="chan2001",
        citation="Chan, Lakonishok & Sougiannis (2001), JF",
        paper_section="Paper-1 §3 R&D intensity construct",
    ),
    LiteratureBind(
        axis="rd_capital",
        bib_key="lev1996",
        citation="Lev & Sougiannis (1996), JAE — R&D capitalization, δ=0.20",
        paper_section="Paper-1 §3 rd_alpha.py capitalisation",
    ),
    LiteratureBind(
        axis="rd_prod",
        bib_key="lev1996",
        citation="Lev & Sougiannis (1996), JAE",
        paper_section="Paper-1 §4 R&D productivity",
    ),
    LiteratureBind(
        axis="rd_gp",
        bib_key="lev1996",
        citation="Lev & Sougiannis (1996), JAE",
        paper_section="Paper-1 §4 gross-profit conversion",
    ),
    LiteratureBind(
        axis="rd_mom",
        bib_key="jegadeesh1993",
        citation="Jegadeesh & Titman (1993), JF — momentum",
        paper_section="Paper-1 §5 R&D momentum tilt",
    ),
    LiteratureBind(
        axis="rd_cap_to_ev",
        bib_key="lev1996",
        citation="Lev & Sougiannis (1996), JAE",
        paper_section="Paper-1 §4 capitalized R&D to EV",
    ),
    # AI Repricing / value (Paper-2)
    LiteratureBind(
        axis="mos_live",
        bib_key="paper2_valuation",
        citation="Paper-2 (AI Repricing) triangulated valuation engine",
        paper_section="Paper-2 §6 valuation triangle / MoS",
    ),
    LiteratureBind(
        axis="mos_snapshot",
        bib_key="paper2_valuation",
        citation="Paper-2 (AI Repricing) triangulated valuation engine",
        paper_section="Paper-2 §6 valuation triangle / MoS",
    ),
    LiteratureBind(
        axis="table20_pass_count",
        bib_key="paper2_table20",
        citation="Paper-2 §8.1 decision tree / Table 20 (12 gates)",
        paper_section="Paper-2 Table 20",
    ),
    LiteratureBind(
        axis="cohort",
        bib_key="paper2_h2",
        citation="Paper-2 H2 over-reaction cohorts (exposed incumbents)",
        paper_section="Paper-2 §5 H2 quintiles",
    ),
    # Quality / profitability
    LiteratureBind(
        axis="roic",
        bib_key="novy2013",
        citation="Novy-Marx (2013), JFE — profitability premium",
        paper_section=None,
    ),
    LiteratureBind(
        axis="gm",
        bib_key="novy2013",
        citation="Novy-Marx (2013), JFE — gross profitability",
        paper_section=None,
    ),
    LiteratureBind(
        axis="fcfm_sbc",
        bib_key="asness2019",
        citation="Asness, Frazzini & Pedersen (2019) — quality minus junk (cash profitability)",
        paper_section="Paper-2 owner-earnings FCF (SBC-adjusted)",
    ),
    LiteratureBind(
        axis="rule40",
        bib_key="saas_unit_econ",
        citation="SaaS unit-economics practice (Rule of 40); Paper-2 quality gate",
        paper_section="Paper-2 §4 quality gates",
    ),
    LiteratureBind(
        axis="offering_quality_z",
        bib_key="util_zscore",
        citation="Sector-robust winsorised z (MAD) — util.py; Asness et al. composite practice",
        paper_section="Paper-2 util.py robust z",
    ),
    # Stickiness / Layer 0
    LiteratureBind(
        axis="retention",
        bib_key="saas_ndr",
        citation="SaaS NRR/NDR disclosure practice; Paper-2 disclose-or-missing overlay",
        paper_section="Paper-2 §7 overlay extractors",
    ),
    LiteratureBind(
        axis="concentration",
        bib_key="saas_ndr",
        citation="Customer-concentration disclosure (10-K Item 1A); Paper-2 overlay",
        paper_section="Paper-2 §7 overlay extractors",
    ),
    # Momentum (price)
    LiteratureBind(
        axis="ret_12m",
        bib_key="jegadeesh1993",
        citation="Jegadeesh & Titman (1993), JF — 12-month momentum",
        paper_section=None,
    ),
    LiteratureBind(
        axis="ret_3m",
        bib_key="jegadeesh1993",
        citation="Jegadeesh & Titman (1993), JF",
        paper_section=None,
    ),
    # Risk / text
    LiteratureBind(
        axis="ai_text_stance",
        bib_key="paper2_text",
        citation="Paper-2 text_exposure — signed augment vs automate stance",
        paper_section="Paper-2 §5 text exposure",
    ),
    LiteratureBind(
        axis="float_fcf_share",
        bib_key="paper2_carveout",
        citation="Paper-2 payments/float carve-out (BILL exclusion rationale)",
        paper_section="Paper-2 §4 carve-outs",
    ),
    # Growth / pre-FCF route
    LiteratureBind(
        axis="rev_cagr",
        bib_key="fama2015",
        citation="Fama & French (2015), JFE — investment/growth factors context",
        paper_section=None,
    ),
    LiteratureBind(
        axis="dilution_ann",
        bib_key="pontiff2008",
        citation="Pontiff & Woodgate (2008), JF — share issuance and returns",
        paper_section=None,
    ),
    LiteratureBind(
        axis="runway_yrs",
        bib_key="paper2_prefcf",
        citation="Paper-2 pre-FCF path-to-profit route (runway/burn constructs)",
        paper_section="Paper-2 §9 pre-FCF route",
    ),
]

_BOUND_AXES = {b.axis for b in LITERATURE_BINDS}


# =============================================================================
# Preset recipes R1–R8 (R9 = runtime custom builder)
# =============================================================================

PRESET_RECIPES: list[RankRecipe] = [
    RankRecipe(
        recipe_id="R1",
        name="Resilient-cheap (Paper-2 H2)",
        formula_human=(
            "Equal-weight MAD robust-z of ROIC, gross margin, and MoS. "
            "Missing axes exclude the name (never imputed)."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes roic×1, gm×1, mos_live×1; "
            "hard: kill_active==False AND carve_out==False; FCF-side route only"
        ),
        hard_filters=["kill_active == False", "carve_out == False"],
        axes=["roic", "gm", "mos_live"],
        benchmark_vs="equal-weight SaaS · software benchmark · naive cheap-only",
    ),
    RankRecipe(
        recipe_id="R2",
        name="Table-20 survivors",
        formula_human=(
            "Hard filter table20_pass_count==12, then weighted MAD robust-z of MoS and R&D productivity."
        ),
        formula_exact=(
            "hard: table20_pass_count==12 AND kill_active==False; "
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); axes mos_live×2, rd_prod×1"
        ),
        hard_filters=["table20_pass_count == 12", "kill_active == False"],
        axes=["mos_live", "rd_prod"],
        benchmark_vs="relaxed 6-of-12 (labeled honestly if shown)",
    ),
    RankRecipe(
        recipe_id="R3",
        name="Sustainable-moat underpriced",
        formula_human=(
            "Weighted MAD robust-z of R&D productivity, SBC-adj FCF margin, ROIC, and "
            "margin of safety. Missing required axes exclude the name (never imputed)."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes rd_prod×1.5, fcfm_sbc×1, roic×1, mos_live×1.5; "
            "hard: kill_active==False AND carve_out==False"
        ),
        hard_filters=["kill_active == False", "carve_out == False"],
        axes=["rd_prod", "fcfm_sbc", "roic", "mos_live"],
        benchmark_vs="high rd_int / low rd_prod (spend without conversion)",
    ),
    RankRecipe(
        recipe_id="R4",
        name="R&D Alpha ETF-style",
        formula_human=(
            "MAD robust-z of R&D intensity, momentum, capitalized R&D, and ROIC (×0.5). "
            "Paper-1 constructs as axes — not a separate /vol ETF wrapper in this engine."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes rd_int×1, rd_mom×1, rd_capital×1, roic×0.5; hard: kill_active==False"
        ),
        hard_filters=["kill_active == False"],
        axes=["rd_int", "rd_mom", "rd_capital", "roic"],
        benchmark_vs="S&P 500 growth of $100 · equal-weight high-RD",
    ),
    RankRecipe(
        recipe_id="R5",
        name="Offering-quality leaders",
        formula_human=(
            "MAD robust-z of offering_quality_z (×2), retention, Rule of 40, and concentration "
            "(lower better). Missing axes exclude."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes offering_quality_z×2, retention×1, rule40×1, concentration×1(higher_better=False); "
            "hard: kill_active==False"
        ),
        hard_filters=["kill_active == False"],
        axes=["offering_quality_z", "retention", "rule40", "concentration"],
        benchmark_vs="segment peers only (HCM vs HCM, EX/CX vs EX/CX)",
    ),
    RankRecipe(
        recipe_id="R6",
        name="Stickiness × value",
        formula_human=(
            "Equal-weight MAD robust-z of disclosed retention and MoS. "
            "Undisclosed retention excludes the name (required axis)."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes retention×1, mos_live×1; hard: kill_active==False; retention required"
        ),
        hard_filters=["kill_active == False", "retention disclosed (required axis)"],
        axes=["retention", "mos_live"],
        benchmark_vs="value-without-stickiness",
    ),
    RankRecipe(
        recipe_id="R7",
        name="Quality-value-momentum composite",
        formula_human=(
            "Equal-weight MAD robust-z of ROIC, GM, SBC-adj FCF margin, MoS, and 12m return."
        ),
        formula_exact=(
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes roic×1, gm×1, fcfm_sbc×1, mos_live×1, ret_12m×1; hard: kill_active==False"
        ),
        hard_filters=["kill_active == False"],
        axes=["roic", "gm", "fcfm_sbc", "mos_live", "ret_12m"],
        benchmark_vs="single-factor sorts",
    ),
    RankRecipe(
        recipe_id="R8",
        name="Pre-FCF path-to-profit",
        formula_human=(
            "Segregated pre-FCF route: MAD robust-z of runway, dilution (lower better), GM, rev CAGR. "
            "Never mixed into FCF+ recipes."
        ),
        formula_exact=(
            "hard: route==pre_fcf AND kill_active==False; "
            "score=Σ w·winsor±3((x-med)/(1.4826·MAD)); "
            "axes runway_yrs×1, dilution_ann×1(higher_better=False), gm×1, rev_cagr×1"
        ),
        hard_filters=["route == pre_fcf", "kill_active == False", "never mixed into FCF+ MoS rank"],
        axes=["runway_yrs", "dilution_ann", "gm", "rev_cagr"],
        benchmark_vs="FCF+ recipes (explicitly segregated)",
    ),
]


def unbound_axes() -> list[tuple[str, str]]:
    """(recipe_id, axis) pairs consumed by presets without a literature bind."""
    missing: list[tuple[str, str]] = []
    for recipe in PRESET_RECIPES:
        for axis in recipe.axes:
            if axis not in _BOUND_AXES:
                missing.append((recipe.recipe_id, axis))
    return missing
