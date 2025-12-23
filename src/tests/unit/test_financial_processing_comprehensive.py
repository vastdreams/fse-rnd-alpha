"""Comprehensive test suite for financial processing logic - testing breaks, error handling, and edge cases."""
import pytest
from unittest.mock import Mock, MagicMock
from src.financials.ratios import calculate_ratios
from src.financials.normaliser import normalize_units, align_fiscal_year, handle_restatements
from src.models.orm.financials_core import FinancialsCore


class TestRatioCalculations:
    """Test financial ratio calculations with edge cases."""
    
    def test_profitability_ratios_basic(self):
        """Test basic profitability ratio calculations."""
        financials = FinancialsCore(
            revenue=1000000.0,
            gross_profit=500000.0,
            operating_income=300000.0,
            net_income=200000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["gross_margin"] == 0.5
        assert ratios["operating_margin"] == 0.3
        assert ratios["net_margin"] == 0.2
    
    def test_rd_intensity_calculation(self):
        """Test R&D intensity calculation."""
        financials = FinancialsCore(
            revenue=1000000.0,
            rd_expense=150000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["rd_intensity"] == 0.15
    
    def test_division_by_zero_revenue(self):
        """Test handling of zero revenue (should not crash)."""
        financials = FinancialsCore(
            revenue=0.0,
            gross_profit=500000.0,
            net_income=200000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not calculate ratios that require revenue
        assert "gross_margin" not in ratios
        assert "net_margin" not in ratios
    
    def test_division_by_zero_negative_revenue(self):
        """Test handling of negative revenue."""
        financials = FinancialsCore(
            revenue=-100000.0,
            net_income=-50000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should handle negative revenue (may calculate ratios or skip)
        # Current implementation would calculate negative ratios
        assert isinstance(ratios, dict)
    
    def test_division_by_zero_equity(self):
        """Test handling of zero equity in ROE calculation."""
        financials = FinancialsCore(
            total_equity=0.0,
            net_income=100000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not calculate ROE if equity is zero
        assert "roe" not in ratios
    
    def test_division_by_zero_assets(self):
        """Test handling of zero assets in ROA calculation."""
        financials = FinancialsCore(
            total_assets=0.0,
            net_income=100000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not calculate ROA if assets are zero
        assert "roa" not in ratios
    
    def test_leverage_ratios(self):
        """Test leverage ratio calculations."""
        financials = FinancialsCore(
            total_equity=500000.0,
            total_assets=1000000.0,
            short_term_debt=200000.0,
            long_term_debt=300000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        total_debt = 200000.0 + 300000.0
        assert ratios["debt_to_equity"] == total_debt / 500000.0
        assert ratios["debt_to_assets"] == total_debt / 1000000.0
    
    def test_leverage_ratios_zero_debt(self):
        """Test leverage ratios when debt is zero."""
        financials = FinancialsCore(
            total_equity=500000.0,
            total_assets=1000000.0,
            short_term_debt=None,
            long_term_debt=None,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not calculate leverage ratios if no debt
        assert "debt_to_equity" not in ratios or ratios.get("debt_to_equity") == 0.0
        assert "debt_to_assets" not in ratios or ratios.get("debt_to_assets") == 0.0
    
    def test_interest_coverage(self):
        """Test interest coverage ratio calculation."""
        financials = FinancialsCore(
            ebit=500000.0,
            interest_expense=50000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["interest_coverage"] == 10.0
    
    def test_interest_coverage_zero_interest(self):
        """Test interest coverage when interest expense is zero."""
        financials = FinancialsCore(
            ebit=500000.0,
            interest_expense=0.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not calculate if interest is zero
        assert "interest_coverage" not in ratios
    
    def test_cfo_to_net_income(self):
        """Test cash flow to net income ratio."""
        financials = FinancialsCore(
            net_income=200000.0,
            cash_from_operations=250000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["cfo_to_net_income"] == 1.25
    
    def test_cfo_to_net_income_zero_income(self):
        """Test CFO to net income when net income is zero."""
        financials = FinancialsCore(
            net_income=0.0,
            cash_from_operations=250000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Current code has bug: checks != 0 but should check == 0
        # Should not calculate if net income is zero
        # This test documents the bug
        assert "cfo_to_net_income" not in ratios or ratios.get("cfo_to_net_income") is None
    
    def test_fcf_calculation(self):
        """Test free cash flow calculation."""
        financials = FinancialsCore(
            cash_from_operations=300000.0,
            capex=-50000.0,
            revenue=1000000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        expected_fcf = 300000.0 - abs(-50000.0)
        assert ratios["fcf"] == expected_fcf
        assert ratios["fcf_margin"] == expected_fcf / 1000000.0
    
    def test_fcf_negative_capex(self):
        """Test FCF with negative capex (outflow)."""
        financials = FinancialsCore(
            cash_from_operations=300000.0,
            capex=-100000.0,  # Negative = outflow
        )
        
        ratios = calculate_ratios(financials)
        
        # Should handle negative capex correctly
        assert ratios["fcf"] == 200000.0
    
    def test_all_none_values(self):
        """Test with all None values (should not crash)."""
        financials = FinancialsCore(
            revenue=None,
            net_income=None,
            total_assets=None,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should return empty dict or dict with None values
        assert isinstance(ratios, dict)
    
    def test_mixed_none_and_values(self):
        """Test with mix of None and actual values."""
        financials = FinancialsCore(
            revenue=1000000.0,
            gross_profit=None,  # Missing
            operating_income=300000.0,
            net_income=None,  # Missing
        )
        
        ratios = calculate_ratios(financials)
        
        # Should calculate what's possible
        assert "gross_margin" not in ratios
        assert ratios["operating_margin"] == 0.3
        assert "net_margin" not in ratios
    
    def test_very_large_numbers(self):
        """Test with very large financial values."""
        financials = FinancialsCore(
            revenue=1e15,  # Very large number
            net_income=1e14,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should handle large numbers without overflow
        assert ratios["net_margin"] == 0.1
    
    def test_very_small_numbers(self):
        """Test with very small financial values."""
        financials = FinancialsCore(
            revenue=0.01,
            net_income=0.001,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should handle small numbers
        assert ratios["net_margin"] == 0.1
    
    def test_negative_ratios(self):
        """Test ratios with negative values."""
        financials = FinancialsCore(
            revenue=1000000.0,
            net_income=-50000.0,  # Loss
        )
        
        ratios = calculate_ratios(financials)
        
        # Should calculate negative ratios
        assert ratios["net_margin"] == -0.05


class TestNormalisation:
    """Test financial data normalization."""
    
    def test_normalize_units_usd_to_usd(self):
        """Test normalization from USD to USD."""
        result = normalize_units(1000000.0, "USD", "USD")
        
        assert result == 1000000.0
    
    def test_normalize_units_stub_implementation(self):
        """Test that stub implementation doesn't crash."""
        result = normalize_units(100.0, "USD/shares", "USD")
        
        # Stub returns as-is
        assert result == 100.0
    
    def test_align_fiscal_year(self):
        """Test fiscal year alignment."""
        data = {
            2022: {"revenue": 1000000},
            2023: {"revenue": 1100000},
        }
        
        result = align_fiscal_year(data, 2023)
        
        assert result == {"revenue": 1100000}
    
    def test_align_fiscal_year_missing(self):
        """Test fiscal year alignment when year is missing."""
        data = {
            2022: {"revenue": 1000000},
        }
        
        result = align_fiscal_year(data, 2023)
        
        assert result is None
    
    def test_handle_restatements(self):
        """Test restatement handling (stub implementation)."""
        data = {
            2022: {"revenue": 1000000},
            2023: {"revenue": 1100000},
        }
        
        result = handle_restatements(data, prefer_latest=True)
        
        # Stub returns as-is
        assert result == data


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_nan_values(self):
        """Test handling of NaN values."""
        import math
        
        financials = FinancialsCore(
            revenue=float('nan'),
            net_income=100000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not crash, but ratios may contain NaN
        assert isinstance(ratios, dict)
    
    def test_infinity_values(self):
        """Test handling of infinity values."""
        import math
        
        financials = FinancialsCore(
            revenue=float('inf'),
            net_income=100000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        # Should not crash
        assert isinstance(ratios, dict)
    
    def test_string_values_should_fail(self):
        """Test that string values cause errors (type validation needed)."""
        # This test documents that type validation is missing
        # In production, should validate types before calculation
        
        financials = Mock()
        financials.revenue = "not_a_number"  # Type error
        
        with pytest.raises((TypeError, AttributeError)):
            # Should fail, but currently may not if FinancialsCore allows strings
            calculate_ratios(financials)


class TestReturnRatios:
    """Test return on equity and assets calculations."""
    
    def test_roe_calculation(self):
        """Test return on equity calculation."""
        financials = FinancialsCore(
            total_equity=1000000.0,
            net_income=100000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["roe"] == 0.1
    
    def test_roa_calculation(self):
        """Test return on assets calculation."""
        financials = FinancialsCore(
            total_assets=2000000.0,
            net_income=200000.0,
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["roa"] == 0.1
    
    def test_negative_returns(self):
        """Test negative returns (losses)."""
        financials = FinancialsCore(
            total_equity=1000000.0,
            net_income=-50000.0,  # Loss
        )
        
        ratios = calculate_ratios(financials)
        
        assert ratios["roe"] == -0.05


class TestDataQualityValidation:
    """Test data quality validation (to be implemented)."""
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_negative_revenue(self):
        """Test validation of negative revenue (should flag as error)."""
        # Would validate that revenue is positive
        pass
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_ratio_ranges(self):
        """Test validation that ratios are within reasonable ranges."""
        # Would validate ratios (e.g., margin between 0 and 1, etc.)
        pass
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_balance_sheet_equity(self):
        """Test validation of balance sheet equation."""
        # Assets = Liabilities + Equity
        pass

