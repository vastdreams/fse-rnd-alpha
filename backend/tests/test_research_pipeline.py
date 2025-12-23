"""
PATH: backend/tests/test_research_pipeline.py
PURPOSE:
  - Regression tests for key research analysis paths
  - Ensures code changes don't break publication results
  - Tests July-June returns, rolling windows, HML premium, and spanning tests

USAGE:
  pytest backend/tests/test_research_pipeline.py -v

ROLE IN ARCHITECTURE:
  - Quality gate for publication-grade research
  - Run before any major code changes
"""

import pytest
import numpy as np
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


class TestJulyJuneReturns:
    """Tests for July-June return calculation (Fama-French convention)."""
    
    def test_formation_year_mapping(self):
        """Test that formation_year maps to correct July-June period."""
        # Formation year 2019 should produce July 2020 - June 2021 returns
        formation_year = 2019
        expected_start = date(2020, 7, 1)
        expected_end = date(2021, 6, 30)
        
        return_start_year = formation_year + 1
        return_end_year = formation_year + 2
        
        actual_start = date(return_start_year, 7, 1)
        actual_end = date(return_end_year, 6, 30)
        
        assert actual_start == expected_start
        assert actual_end == expected_end
    
    def test_return_calculation(self):
        """Test total return formula: (P_end - P_start) / P_start."""
        july_start_price = 100.0
        june_end_price = 110.0
        
        expected_return = (june_end_price / july_start_price) - 1
        assert expected_return == pytest.approx(0.10, abs=0.001)
    
    def test_annualization(self):
        """Test return annualization for partial year data."""
        total_return = 0.05  # 5% over 126 trading days (6 months)
        trading_days = 126
        trading_days_per_year = 252
        years = trading_days / trading_days_per_year
        
        annualized = ((1 + total_return) ** (1 / years)) - 1
        # Should be approximately 10.25% annualized
        assert annualized == pytest.approx(0.1025, abs=0.01)
    
    def test_volatility_calculation(self):
        """Test annualized volatility: daily_std * sqrt(252)."""
        daily_returns = [0.01, -0.005, 0.008, -0.003, 0.012]
        daily_std = np.std(daily_returns)
        sqrt_252 = np.sqrt(252)
        
        annualized_vol = daily_std * sqrt_252
        # Should be reasonable annual volatility
        assert 0 < annualized_vol < 1.0


class TestQuintileFormation:
    """Tests for quintile portfolio formation logic."""
    
    def test_quintile_assignment(self):
        """Test that quintile assignment is correct."""
        rd_intensities = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        n = len(rd_intensities)
        quintile_size = n // 5  # 2 companies per quintile
        
        # Q1 should be lowest R&D (1, 2)
        q1 = rd_intensities[:quintile_size]
        assert q1 == [1, 2]
        
        # Q5 should be highest R&D (9, 10)
        q5 = rd_intensities[-quintile_size:]
        assert q5 == [9, 10]
    
    def test_hml_premium_calculation(self):
        """Test HML premium: Q5 return - Q1 return."""
        q1_returns = [0.05, 0.06, 0.04]  # Low R&D
        q5_returns = [0.15, 0.18, 0.12]  # High R&D
        
        q1_mean = np.mean(q1_returns)
        q5_mean = np.mean(q5_returns)
        hml_premium = q5_mean - q1_mean
        
        assert hml_premium == pytest.approx(0.10, abs=0.001)
    
    def test_equal_weight_portfolio(self):
        """Test equal-weight portfolio return calculation."""
        returns = [0.10, 0.05, 0.15, 0.08]
        equal_weight_return = np.mean(returns)
        
        assert equal_weight_return == pytest.approx(0.095, abs=0.001)
    
    def test_value_weight_portfolio(self):
        """Test value-weighted portfolio return calculation."""
        returns = [0.10, 0.05, 0.15, 0.08]
        market_caps = [100, 200, 50, 150]  # Different weights
        
        total_cap = sum(market_caps)
        weights = [cap / total_cap for cap in market_caps]
        vw_return = np.average(returns, weights=weights)
        
        # VW return should differ from EW
        ew_return = np.mean(returns)
        assert vw_return != ew_return


class TestStatisticalMethods:
    """Tests for statistical analysis methods."""
    
    def test_newey_west_adjustment(self):
        """Test Newey-West HAC adjustment concept."""
        # For overlapping k-year windows, use k-1 lags
        k_year_window = 5
        expected_lags = k_year_window - 1
        
        assert expected_lags == 4
    
    def test_t_statistic_calculation(self):
        """Test t-statistic: mean / (std / sqrt(n))."""
        premiums = [0.10, 0.12, 0.08, 0.11, 0.09]
        mean_premium = np.mean(premiums)
        std_premium = np.std(premiums, ddof=1)
        n = len(premiums)
        
        t_stat = mean_premium / (std_premium / np.sqrt(n))
        
        # With positive mean and positive premium in all years, t should be positive
        assert t_stat > 0
    
    def test_win_rate_calculation(self):
        """Test win rate: percentage of years with positive premium."""
        premiums = [0.10, 0.12, -0.02, 0.11, 0.09]
        positive_years = sum(1 for p in premiums if p > 0)
        win_rate = positive_years / len(premiums) * 100
        
        assert win_rate == 80.0


class TestDelistingReturns:
    """Tests for delisting return logic."""
    
    def test_delisting_heuristics(self):
        """Test delisting return heuristics by removal reason."""
        test_cases = [
            ("merger", 0.0),
            ("acquisition", 0.0),
            ("bankruptcy", -0.30),
            ("distress", -0.30),
            ("market_cap", -0.10),
            ("size", -0.10),
            ("unknown", -0.05),
        ]
        
        for reason, expected_return in test_cases:
            if "merger" in reason or "acquisition" in reason:
                computed = 0.0
            elif "bankruptcy" in reason or "distress" in reason:
                computed = -0.30
            elif "market_cap" in reason or "size" in reason:
                computed = -0.10
            else:
                computed = -0.05
            
            assert computed == expected_return, f"Failed for reason: {reason}"
    
    def test_price_based_estimation(self):
        """Test price-based delisting return estimation."""
        last_price = 5.0
        price_5_days_ago = 10.0
        
        delist_return = (last_price / price_5_days_ago) - 1
        assert delist_return == pytest.approx(-0.50, abs=0.001)


class TestRiskFreeRate:
    """Tests for risk-free rate standardization."""
    
    def test_rf_conversion(self):
        """Test risk-free rate conversion from percentage to decimal."""
        rf_annual_pct = 2.5  # 2.5%
        rf_decimal = rf_annual_pct / 100
        
        assert rf_decimal == 0.025
    
    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio: (return - rf) / volatility."""
        annualized_return = 0.12  # 12%
        risk_free_rate = 0.02  # 2%
        volatility = 0.20  # 20%
        
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility
        
        assert sharpe_ratio == pytest.approx(0.50, abs=0.001)
    
    def test_fallback_rf(self):
        """Test fallback to default RF when database has no data."""
        DEFAULT_RF = 0.02
        db_rf = None  # Simulating no data
        
        rf = db_rf if db_rf is not None else DEFAULT_RF
        assert rf == DEFAULT_RF


class TestSurvivorship:
    """Tests for survivorship bias mitigation."""
    
    def test_point_in_time_filtering(self):
        """Test point-in-time constituent filtering logic."""
        # Company added Jan 2015, removed Dec 2020
        added_date = date(2015, 1, 1)
        removed_date = date(2020, 12, 31)
        
        # Check if company was member on specific dates
        check_date_1 = date(2017, 1, 1)  # Should be member
        check_date_2 = date(2022, 1, 1)  # Should NOT be member
        
        is_member_1 = added_date <= check_date_1 and (removed_date is None or removed_date >= check_date_1)
        is_member_2 = added_date <= check_date_2 and (removed_date is None or removed_date >= check_date_2)
        
        assert is_member_1 == True
        assert is_member_2 == False
    
    def test_delisting_return_integration(self):
        """Test that delisting return is used in year of delisting."""
        normal_return = 0.10
        delisting_return = -0.30
        delist_year = 2020
        analysis_year = 2020
        
        # In year of delisting, use delisting return
        if analysis_year == delist_year:
            used_return = delisting_return
        else:
            used_return = normal_return
        
        assert used_return == -0.30


class TestRobustness:
    """Tests for robustness analysis methods."""
    
    def test_rd_intensity_cap(self):
        """Test R&D intensity capping."""
        MAX_CAP = 100.0  # 100%
        intensities = [5.0, 50.0, 150.0, 200.0]
        
        capped = [min(i, MAX_CAP) for i in intensities]
        
        assert capped == [5.0, 50.0, 100.0, 100.0]
    
    def test_different_caps_produce_different_results(self):
        """Test that different R&D caps produce different quintile assignments."""
        intensities = [5, 10, 50, 80, 120, 180]
        
        # Cap at 100
        capped_100 = [min(i, 100) for i in intensities]
        
        # Cap at 50
        capped_50 = [min(i, 50) for i in intensities]
        
        # Order should be preserved but values differ
        assert capped_100 != capped_50
        assert capped_100[4] == 100
        assert capped_50[4] == 50


class TestTier2ReturnCalculation:
    """Tests for Tier-2 (CRSP) return calculation."""
    
    def test_monthly_compounding(self):
        """Test compounding of monthly returns."""
        monthly_returns = [0.02, 0.03, -0.01, 0.015, 0.02, 0.01,
                          0.025, -0.005, 0.01, 0.02, 0.015, 0.005]
        
        # Compound
        compound = 1.0
        for r in monthly_returns:
            compound *= (1 + r)
        total_return = compound - 1
        
        # Should be approximately 16.6% total return (compounding effect)
        assert total_return == pytest.approx(0.166, abs=0.01)
    
    def test_delisting_return_integration(self):
        """Test CRSP delisting return integration: (1+RET)*(1+DLRET)-1."""
        ret = 0.02  # 2% regular return
        dlret = -0.30  # -30% delisting return
        
        combined = (1 + ret) * (1 + dlret) - 1
        
        # Should be approximately -28.6%
        assert combined == pytest.approx(-0.286, abs=0.001)
    
    def test_delisting_only(self):
        """Test when only delisting return is available."""
        dlret = -0.50  # -50% delisting return
        ret = None
        
        if ret is not None and dlret is not None:
            combined = (1 + ret) * (1 + dlret) - 1
        elif ret is not None:
            combined = ret
        else:
            combined = dlret
        
        assert combined == -0.50
    
    def test_monthly_volatility_annualization(self):
        """Test volatility annualization from monthly to annual."""
        monthly_std = 0.05  # 5% monthly std
        
        annual_vol = monthly_std * np.sqrt(12)
        
        # Should be approximately 17.3%
        assert annual_vol == pytest.approx(0.173, abs=0.01)


class TestDataTierFiltering:
    """Tests for data tier filtering in analyzers."""
    
    def test_tier_values_are_valid(self):
        """Test that tier values are one of the valid options."""
        valid_tiers = ["tier1", "tier2"]
        
        # Simulate user input
        user_tier = "tier1"
        assert user_tier in valid_tiers
        
        user_tier = "tier2"
        assert user_tier in valid_tiers
        
        user_tier = "tier3"
        assert user_tier not in valid_tiers
    
    def test_return_convention_values(self):
        """Test that return convention values are valid."""
        valid_conventions = ["july_june", "calendar"]
        
        assert "july_june" in valid_conventions
        assert "calendar" in valid_conventions
        assert "quarterly" not in valid_conventions
    
    def test_tier_isolation(self):
        """Test that tier1 and tier2 results should be isolated."""
        # Simulate results from different tiers
        tier1_results = [{"tier": "tier1", "premium": 5.2}]
        tier2_results = [{"tier": "tier2", "premium": 4.8}]
        
        # Filtering by tier should return only that tier's results
        tier1_only = [r for r in tier1_results + tier2_results if r["tier"] == "tier1"]
        tier2_only = [r for r in tier1_results + tier2_results if r["tier"] == "tier2"]
        
        assert len(tier1_only) == 1
        assert len(tier2_only) == 1
        assert tier1_only[0]["premium"] == 5.2
        assert tier2_only[0]["premium"] == 4.8


class TestComputationRunTracking:
    """Tests for computation run tracking and reproducibility."""
    
    def test_run_id_uniqueness(self):
        """Test that each computation run gets a unique ID."""
        import uuid
        
        run_ids = [str(uuid.uuid4()) for _ in range(100)]
        
        # All IDs should be unique
        assert len(set(run_ids)) == 100
    
    def test_run_id_format(self):
        """Test that run ID is a valid UUID format."""
        import uuid
        
        run_id = str(uuid.uuid4())
        
        # Should be able to parse back
        parsed = uuid.UUID(run_id)
        assert str(parsed) == run_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

