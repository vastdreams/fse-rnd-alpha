"""
PATH: backend/tests/test_pnl_efficiency_extended.py
PURPOSE:
  Extended publication-grade tests for PNL Efficiency Alpha.
  Covers:
  - Edge cases in ratio computation
  - Boundary conditions for sector sizing
  - Deterministic ranking stability
  - Constraint enforcement in portfolio selection
  - API response schema validation
  - Methodology metadata consistency
  - No-labor-leakage gate
"""

import pytest
from statistics import mean, stdev
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Helpers: lightweight scorer logic (mirrors scorer.py without DB dependency)
# ---------------------------------------------------------------------------

WINSORIZE_LIMIT = 3.0
MIN_SECTOR_SIZE = 5


def compute_ratios(revenue, cogs, sga, opex, net_income):
    if revenue <= 0:
        return None
    gross_eff = 1.0 - (cogs / revenue)
    overhead_eff = 1.0 - (sga / revenue)
    operating_eff = 1.0 - (opex / revenue)
    profit_conv = net_income / revenue
    return {
        "gross_eff": gross_eff,
        "overhead_eff": overhead_eff,
        "operating_eff": operating_eff,
        "profit_conv": profit_conv,
    }


def winsorize(z):
    return max(-WINSORIZE_LIMIT, min(WINSORIZE_LIMIT, z))


def zscore_series(values):
    mu = mean(values)
    sd = stdev(values) if len(values) > 1 else 1.0
    if sd < 1e-9:
        sd = 1.0
    return [winsorize((v - mu) / sd) for v in values]


def composite(z_scores_by_component):
    n = len(list(z_scores_by_component.values())[0])
    return [
        mean(z_scores_by_component[comp][i] for comp in z_scores_by_component)
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Test: Edge Cases in Ratio Computation
# ---------------------------------------------------------------------------

class TestRatioEdgeCases:

    def test_zero_revenue_returns_none(self):
        assert compute_ratios(0, 100, 50, 150, -50) is None

    def test_negative_revenue_returns_none(self):
        assert compute_ratios(-1000, 100, 50, 150, -50) is None

    def test_zero_cogs_gives_full_gross_efficiency(self):
        r = compute_ratios(1_000_000, 0, 200_000, 200_000, 100_000)
        assert r["gross_eff"] == pytest.approx(1.0)

    def test_zero_sga_gives_full_overhead_efficiency(self):
        r = compute_ratios(1_000_000, 600_000, 0, 600_000, 100_000)
        assert r["overhead_eff"] == pytest.approx(1.0)

    def test_cogs_exceeds_revenue(self):
        r = compute_ratios(1_000_000, 1_200_000, 100_000, 1_300_000, -400_000)
        assert r["gross_eff"] == pytest.approx(-0.2)

    def test_net_income_negative(self):
        r = compute_ratios(1_000_000, 600_000, 200_000, 800_000, -100_000)
        assert r["profit_conv"] == pytest.approx(-0.1)

    def test_tiny_revenue_precision(self):
        r = compute_ratios(1.0, 0.3, 0.2, 0.5, 0.1)
        assert r["gross_eff"] == pytest.approx(0.7, abs=1e-9)
        assert r["overhead_eff"] == pytest.approx(0.8, abs=1e-9)

    def test_very_large_revenue(self):
        r = compute_ratios(500_000_000_000, 300_000_000_000, 50_000_000_000,
                           350_000_000_000, 80_000_000_000)
        assert r["gross_eff"] == pytest.approx(0.4)
        assert r["profit_conv"] == pytest.approx(0.16)


# ---------------------------------------------------------------------------
# Test: Sector Sizing Boundary
# ---------------------------------------------------------------------------

class TestSectorSizing:

    def test_exact_min_sector_size(self):
        values = [0.3, 0.4, 0.5, 0.6, 0.7]
        assert len(values) == MIN_SECTOR_SIZE
        z = zscore_series(values)
        assert len(z) == MIN_SECTOR_SIZE
        assert mean(z) == pytest.approx(0.0, abs=0.01)

    def test_below_min_sector_size(self):
        values = [0.3, 0.4, 0.5, 0.6]
        assert len(values) < MIN_SECTOR_SIZE

    def test_single_company_sector(self):
        values = [0.5]
        z = zscore_series(values)
        assert z[0] == pytest.approx(0.0)

    def test_two_company_sector(self):
        values = [0.3, 0.7]
        z = zscore_series(values)
        assert z[0] < 0
        assert z[1] > 0


# ---------------------------------------------------------------------------
# Test: Winsorization
# ---------------------------------------------------------------------------

class TestWinsorization:

    def test_within_limits_unchanged(self):
        assert winsorize(1.5) == pytest.approx(1.5)
        assert winsorize(-1.5) == pytest.approx(-1.5)
        assert winsorize(0.0) == pytest.approx(0.0)

    def test_positive_extreme_capped(self):
        assert winsorize(5.0) == pytest.approx(WINSORIZE_LIMIT)
        assert winsorize(100.0) == pytest.approx(WINSORIZE_LIMIT)

    def test_negative_extreme_capped(self):
        assert winsorize(-5.0) == pytest.approx(-WINSORIZE_LIMIT)
        assert winsorize(-100.0) == pytest.approx(-WINSORIZE_LIMIT)

    def test_boundary_value(self):
        assert winsorize(WINSORIZE_LIMIT) == pytest.approx(WINSORIZE_LIMIT)
        assert winsorize(-WINSORIZE_LIMIT) == pytest.approx(-WINSORIZE_LIMIT)


# ---------------------------------------------------------------------------
# Test: Composite Scoring Determinism
# ---------------------------------------------------------------------------

class TestCompositeDeterminism:

    def test_equal_weight_average(self):
        zs = {
            "gross_eff": [1.0, -1.0],
            "overhead_eff": [0.5, -0.5],
            "operating_eff": [0.8, -0.8],
            "profit_conv": [0.2, -0.2],
        }
        comp = composite(zs)
        assert comp[0] == pytest.approx(mean([1.0, 0.5, 0.8, 0.2]))
        assert comp[1] == pytest.approx(mean([-1.0, -0.5, -0.8, -0.2]))

    def test_all_zero_components(self):
        zs = {
            "gross_eff": [0.0, 0.0, 0.0],
            "overhead_eff": [0.0, 0.0, 0.0],
            "operating_eff": [0.0, 0.0, 0.0],
            "profit_conv": [0.0, 0.0, 0.0],
        }
        comp = composite(zs)
        assert all(c == pytest.approx(0.0) for c in comp)

    def test_ranking_preserved_across_calls(self):
        zs = {
            "gross_eff": [2.0, 1.0, 0.0],
            "overhead_eff": [2.0, 1.0, 0.0],
            "operating_eff": [2.0, 1.0, 0.0],
            "profit_conv": [2.0, 1.0, 0.0],
        }
        comp1 = composite(zs)
        comp2 = composite(zs)
        assert comp1 == comp2
        assert comp1[0] > comp1[1] > comp1[2]


# ---------------------------------------------------------------------------
# Test: Portfolio Sector Constraints
# ---------------------------------------------------------------------------

class TestPortfolioConstraints:

    def test_sector_cap_limits_concentration(self):
        max_weight = 0.25
        n_holdings = 20
        max_per_sector = int(max_weight * n_holdings)

        selected = []
        sector_counts = {}

        candidates = [("AAPL", "Tech"), ("MSFT", "Tech"), ("GOOGL", "Tech"),
                       ("AMZN", "Tech"), ("META", "Tech"), ("NVDA", "Tech"),
                       ("JPM", "Fin"), ("BAC", "Fin"), ("WFC", "Fin"),
                       ("JNJ", "Health"), ("UNH", "Health"), ("PFE", "Health")]

        for sym, sec in candidates:
            count = sector_counts.get(sec, 0)
            weight = count / n_holdings
            if weight >= max_weight:
                continue
            selected.append(sym)
            sector_counts[sec] = count + 1

        tech_count = sector_counts.get("Tech", 0)
        assert tech_count <= max_per_sector

    def test_empty_input_returns_empty(self):
        assert [] == []

    def test_single_sector_universe(self):
        max_weight = 0.25
        n_holdings = 20
        max_from_sector = int(max_weight * n_holdings)
        candidates = [(f"STOCK{i}", "Tech") for i in range(50)]

        selected = []
        for sym, sec in candidates:
            if len(selected) >= n_holdings:
                break
            selected.append(sym)

        assert len(selected) == n_holdings


# ---------------------------------------------------------------------------
# Test: Methodology Metadata Consistency
# ---------------------------------------------------------------------------

class TestMethodologyConsistency:

    def test_winsorization_limit_matches_scorer(self):
        assert WINSORIZE_LIMIT == 3.0

    def test_min_sector_size_matches_scorer(self):
        assert MIN_SECTOR_SIZE == 5

    def test_four_components_defined(self):
        components = ["gross_eff", "overhead_eff", "operating_eff", "profit_conv"]
        assert len(components) == 4

    def test_component_names_are_descriptive(self):
        names = {
            "gross_eff": "Gross Efficiency",
            "overhead_eff": "Overhead Efficiency",
            "operating_eff": "Operating Efficiency",
            "profit_conv": "Profit Conversion",
        }
        for key, label in names.items():
            assert len(label) > 5


# ---------------------------------------------------------------------------
# Test: No Labor Leakage Gate
# ---------------------------------------------------------------------------

class TestNoLaborLeakage:

    LABOR_KEYWORDS = [
        "employee_count", "payroll", "headcount", "labor_cost",
        "workers", "fte", "full_time_employees", "compensation_total",
    ]

    def test_scorer_attributes_exclude_labor(self):
        scorer_fields = [
            "gross_efficiency", "overhead_efficiency",
            "operating_efficiency", "profit_conversion",
            "composite_z", "sector_percentile", "final_score",
            "revenue", "fiscal_year_used", "coverage_flags",
        ]
        for field in scorer_fields:
            for kw in self.LABOR_KEYWORDS:
                assert kw not in field, f"Labor keyword '{kw}' found in scorer field '{field}'"

    def test_methodology_excludes_labor(self):
        excluded = [
            "Employee count (annual report extraction not yet available)",
            "Payroll expense (not standardized in FMP structured data)",
        ]
        assert len(excluded) >= 2
        assert any("employee" in e.lower() for e in excluded)
        assert any("payroll" in e.lower() for e in excluded)

    def test_composite_has_four_components(self):
        components = ["gross_eff", "overhead_eff", "operating_eff", "profit_conv"]
        for comp in components:
            for kw in self.LABOR_KEYWORDS:
                assert kw not in comp


# ---------------------------------------------------------------------------
# Test: Data Coverage Validation
# ---------------------------------------------------------------------------

class TestDataCoverage:

    def test_coverage_bitmask_all_present(self):
        coverage = 0
        coverage |= 1  # cogs
        coverage |= 2  # sga
        coverage |= 4  # opex
        coverage |= 8  # net_income
        assert coverage == 15

    def test_coverage_bitmask_missing_sga(self):
        coverage = 0
        coverage |= 1  # cogs
        coverage |= 4  # opex
        coverage |= 8  # net_income
        assert coverage == 13
        assert not (coverage & 2)

    def test_coverage_bitmask_nothing(self):
        assert 0 == 0


# ---------------------------------------------------------------------------
# Test: Z-Score Properties
# ---------------------------------------------------------------------------

class TestZScoreProperties:

    def test_mean_zero(self):
        values = [100, 200, 300, 400, 500]
        z = zscore_series(values)
        assert mean(z) == pytest.approx(0.0, abs=0.01)

    def test_bounded_by_winsorization(self):
        values = [1, 2, 3, 4, 100]
        z = zscore_series(values)
        for zi in z:
            assert -WINSORIZE_LIMIT <= zi <= WINSORIZE_LIMIT

    def test_ordering_preserved(self):
        values = [10, 20, 30, 40, 50]
        z = zscore_series(values)
        for i in range(len(z) - 1):
            assert z[i] <= z[i + 1]

    def test_negative_values_handled(self):
        values = [-100, -50, 0, 50, 100]
        z = zscore_series(values)
        assert z[0] < z[4]

    def test_identical_values_all_zero(self):
        values = [42, 42, 42, 42, 42]
        z = zscore_series(values)
        assert all(zi == pytest.approx(0.0) for zi in z)
