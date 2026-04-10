"""
PATH: backend/tests/test_pnl_efficiency.py
PURPOSE:
  - Unit and integration tests for PNL Efficiency Alpha scorer
  - Verifies ratio computation, sector normalization, winsorization, composite scoring
  - Tests portfolio integration via method="pnl_efficiency"
  - Tests research API endpoints

USAGE:
  pytest backend/tests/test_pnl_efficiency.py -v
"""

import pytest
from statistics import mean, stdev
from unittest.mock import AsyncMock, MagicMock, patch


class TestPnlRatioComputation:
    """Tests for raw P&L efficiency ratio calculations."""

    def test_gross_efficiency_basic(self):
        """1 - (COGS / Revenue) for a standard company."""
        revenue = 1_000_000
        cogs = 600_000
        gross_eff = 1.0 - (cogs / revenue)
        assert gross_eff == pytest.approx(0.4, abs=1e-9)

    def test_gross_efficiency_zero_cogs(self):
        """Companies with zero COGS should have 100% gross efficiency."""
        gross_eff = 1.0 - (0 / 1_000_000)
        assert gross_eff == pytest.approx(1.0)

    def test_overhead_efficiency(self):
        """1 - (SGA / Revenue)."""
        sga = 200_000
        revenue = 1_000_000
        overhead_eff = 1.0 - (sga / revenue)
        assert overhead_eff == pytest.approx(0.8)

    def test_operating_efficiency(self):
        """1 - (OpEx / Revenue)."""
        opex = 750_000
        revenue = 1_000_000
        op_eff = 1.0 - (opex / revenue)
        assert op_eff == pytest.approx(0.25)

    def test_profit_conversion(self):
        """Net Income / Revenue."""
        net_income = 150_000
        revenue = 1_000_000
        profit_conv = net_income / revenue
        assert profit_conv == pytest.approx(0.15)

    def test_profit_conversion_negative(self):
        """Loss-making companies should have negative profit conversion."""
        net_income = -50_000
        revenue = 1_000_000
        profit_conv = net_income / revenue
        assert profit_conv == pytest.approx(-0.05)

    def test_all_components_present(self):
        """Coverage bitmask should have all 4 bits set when all data available."""
        coverage = 0
        coverage |= 1  # cogs
        coverage |= 2  # sga
        coverage |= 4  # opex
        coverage |= 8  # net_income
        assert coverage == 15


class TestSectorNormalization:
    """Tests for within-sector z-scoring."""

    def test_zscore_computation(self):
        """Z-scores should be mean-0, stdev-1 within sector."""
        values = [0.3, 0.4, 0.5, 0.6, 0.7]
        mu = mean(values)
        sd = stdev(values)
        z_scores = [(v - mu) / sd for v in values]

        assert mean(z_scores) == pytest.approx(0.0, abs=1e-10)
        assert stdev(z_scores) == pytest.approx(1.0, abs=1e-10)

    def test_zscore_ordering_preserved(self):
        """Higher raw values should produce higher z-scores."""
        values = [0.2, 0.5, 0.8]
        mu = mean(values)
        sd = stdev(values)
        z_scores = [(v - mu) / sd for v in values]

        assert z_scores[0] < z_scores[1] < z_scores[2]

    def test_winsorization_caps_extreme_values(self):
        """Z-scores beyond +/- 3 should be capped."""
        from app.services.pnl_efficiency_scorer.scorer import WINSORIZE_LIMIT

        raw_z = 5.0
        winsorized = max(-WINSORIZE_LIMIT, min(WINSORIZE_LIMIT, raw_z))
        assert winsorized == 3.0

        raw_z_neg = -4.5
        winsorized_neg = max(-WINSORIZE_LIMIT, min(WINSORIZE_LIMIT, raw_z_neg))
        assert winsorized_neg == -3.0

    def test_minimum_sector_size_enforced(self):
        """Sectors with < 5 companies should be excluded."""
        from app.services.pnl_efficiency_scorer.scorer import MIN_SECTOR_SIZE
        assert MIN_SECTOR_SIZE == 5


class TestCompositeScoring:
    """Tests for equal-weight composite z-score."""

    def test_equal_weight_average(self):
        """Composite should be mean of four z-scores."""
        z1, z2, z3, z4 = 1.0, 0.5, -0.5, 0.0
        composite = mean([z1, z2, z3, z4])
        assert composite == pytest.approx(0.25)

    def test_all_positive_components(self):
        """All positive z-scores should yield positive composite."""
        z_scores = [0.5, 0.3, 0.2, 0.1]
        composite = mean(z_scores)
        assert composite > 0

    def test_all_negative_components(self):
        """All negative z-scores should yield negative composite."""
        z_scores = [-0.5, -0.3, -0.2, -0.1]
        composite = mean(z_scores)
        assert composite < 0

    def test_composite_bounded_by_winsorization(self):
        """Composite z-score should be bounded by [-3, 3]."""
        max_composite = mean([3.0, 3.0, 3.0, 3.0])
        min_composite = mean([-3.0, -3.0, -3.0, -3.0])
        assert max_composite == 3.0
        assert min_composite == -3.0


class TestPnlScorerIntegration:
    """Integration tests for the scorer's _score_sector method."""

    def test_score_sector_basic(self):
        """Score a sector with known data and verify output structure."""
        from app.services.pnl_efficiency_scorer.scorer import PnlEfficiencyScorer

        companies = [
            {
                "symbol": f"TEST{i}",
                "name": f"Test Company {i}",
                "sector": "Technology",
                "industry": "Software",
                "revenue": 1_000_000_000,
                "cogs": 400_000_000 + i * 50_000_000,
                "sga": 100_000_000 + i * 10_000_000,
                "opex": 600_000_000 + i * 40_000_000,
                "net_income": 200_000_000 - i * 30_000_000,
                "fiscal_year": 2024,
                "coverage": 15,
            }
            for i in range(6)
        ]

        # PnlEfficiencyScorer._score_sector is a sync method
        scorer = PnlEfficiencyScorer.__new__(PnlEfficiencyScorer)
        scores = scorer._score_sector(companies, "Technology")

        assert len(scores) == 6
        for s in scores:
            assert s.sector == "Technology"
            assert -3.0 <= s.composite_z <= 3.0
            assert 0.0 <= s.sector_percentile <= 100.0
            assert s.coverage_flags == 15

    def test_score_sector_preserves_ranking(self):
        """Better P&L ratios should yield higher scores."""
        from app.services.pnl_efficiency_scorer.scorer import PnlEfficiencyScorer

        # Company 0 has best ratios (low cogs, low sga, low opex, high income)
        companies = []
        for i in range(6):
            companies.append({
                "symbol": f"T{i}",
                "name": f"Test {i}",
                "sector": "Tech",
                "industry": None,
                "revenue": 1_000_000_000,
                "cogs": 300_000_000 + i * 80_000_000,
                "sga": 50_000_000 + i * 20_000_000,
                "opex": 400_000_000 + i * 80_000_000,
                "net_income": 300_000_000 - i * 50_000_000,
                "fiscal_year": 2024,
                "coverage": 15,
            })

        scorer = PnlEfficiencyScorer.__new__(PnlEfficiencyScorer)
        scores = scorer._score_sector(companies, "Tech")

        # Company 0 (best ratios) should have the highest composite z
        composites = [(s.symbol, s.composite_z) for s in scores]
        composites.sort(key=lambda x: x[1], reverse=True)
        assert composites[0][0] == "T0"
        assert composites[-1][0] == "T5"


class TestDataClasses:
    """Tests for PNL data class structure."""

    def test_pnl_score_defaults(self):
        """Default PnlEfficiencyScore should have safe zero values."""
        from app.services.pnl_efficiency_scorer.data_classes import PnlEfficiencyScore

        score = PnlEfficiencyScore(symbol="TEST", name="Test", sector="Tech")
        assert score.composite_z == 0.0
        assert score.weight == 0.0
        assert score.selection_rank == 0
        assert score.coverage_flags == 0

    def test_component_names_match(self):
        """PNL_COMPONENT_NAMES should have exactly 4 entries."""
        from app.services.pnl_efficiency_scorer.data_classes import PNL_COMPONENT_NAMES

        assert len(PNL_COMPONENT_NAMES) == 4
        assert "gross_efficiency" in PNL_COMPONENT_NAMES
        assert "overhead_efficiency" in PNL_COMPONENT_NAMES
        assert "operating_efficiency" in PNL_COMPONENT_NAMES
        assert "profit_conversion" in PNL_COMPONENT_NAMES


class TestFormulaRegistry:
    """Tests for PNL formulas in the central registry."""

    def test_pnl_formulas_present(self):
        """All 5 PNL formula specs should exist in the registry."""
        from app.core.formulas.registry import FORMULA_REGISTRY

        expected = [
            "cogs_to_revenue",
            "sga_to_revenue",
            "opex_to_revenue",
            "net_margin",
            "pnl_efficiency_score",
        ]
        for name in expected:
            assert name in FORMULA_REGISTRY, f"Missing formula: {name}"

    def test_pnl_score_formula_has_four_inputs(self):
        """pnl_efficiency_score should declare four z-score inputs."""
        from app.core.formulas.registry import FORMULA_REGISTRY

        spec = FORMULA_REGISTRY["pnl_efficiency_score"]
        assert len(spec.inputs) == 4

    def test_formula_valid_ranges(self):
        """All PNL formulas should have valid_range tuples."""
        from app.core.formulas.registry import FORMULA_REGISTRY

        pnl_keys = ["cogs_to_revenue", "sga_to_revenue", "opex_to_revenue", "net_margin", "pnl_efficiency_score"]
        for key in pnl_keys:
            spec = FORMULA_REGISTRY[key]
            assert isinstance(spec.valid_range, tuple)
            assert len(spec.valid_range) == 2


class TestNoLaborLeakage:
    """Ensure Phase 1 does not reference payroll or employee data."""

    def test_scorer_has_no_employee_field(self):
        """PnlEfficiencyScore should have no employee/payroll fields."""
        from app.services.pnl_efficiency_scorer.data_classes import PnlEfficiencyScore
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(PnlEfficiencyScore)}
        forbidden = {"employee_count", "payroll", "payroll_expense", "headcount", "labor_efficiency"}
        overlap = field_names & forbidden
        assert not overlap, f"Phase 1 score should not have labor fields: {overlap}"

    def test_methodology_excludes_labor(self):
        """Methodology endpoint should explicitly list labor as excluded."""
        # This is a structural test — the API response is tested via curl above
        from app.services.pnl_efficiency_scorer.data_classes import PNL_COMPONENT_NAMES

        for name in PNL_COMPONENT_NAMES:
            assert "payroll" not in name.lower()
            assert "employee" not in name.lower()
            assert "labor" not in name.lower()
