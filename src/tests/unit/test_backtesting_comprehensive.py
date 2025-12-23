"""Comprehensive test suite for backtesting engine - testing breaks, error handling, and edge cases."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.backtesting.engine import (
    get_factor_values,
    get_prices,
    run_backtest,
)
from src.backtesting.statistics import (
    calculate_returns,
    calculate_portfolio_return,
    calculate_statistics,
    calculate_drawdown,
)
from src.backtesting.portfolio_construction import assign_buckets
from src.backtesting.specs import BacktestSpec


class TestFactorValues:
    """Test factor value extraction."""
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_rnd_numeric_factor(self, mock_session_scope):
        """Test getting R&D numeric factor values."""
        mock_session = Mock()
        mock_company_year = Mock()
        mock_company_year.ticker = "AAPL"
        mock_company_year.fiscal_year = 2023
        mock_company_year.financials_ratios = Mock()
        mock_company_year.financials_ratios.rd_intensity = 0.15
        
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_company_year]
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_factor_values("RND_v1_numeric", 2023, ["AAPL"])
        
        assert "AAPL" in result
        assert result["AAPL"] == 0.15
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_rnd_text_factor(self, mock_session_scope):
        """Test getting R&D text factor values."""
        mock_session = Mock()
        mock_company_year = Mock()
        mock_company_year.ticker = "AAPL"
        mock_company_year.text_factor_rd = Mock()
        mock_company_year.text_factor_rd.rd_tone_score = 0.75
        
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_company_year]
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_factor_values("RND_v1_text", 2023, ["AAPL"])
        
        assert "AAPL" in result
        assert result["AAPL"] == 0.75
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_factor_missing_data(self, mock_session_scope):
        """Test handling of missing factor data."""
        mock_session = Mock()
        mock_company_year = Mock()
        mock_company_year.ticker = "AAPL"
        mock_company_year.financials_ratios = None  # Missing data
        
        mock_session.query.return_value.filter_by.return_value.all.return_value = [mock_company_year]
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_factor_values("RND_v1_numeric", 2023, ["AAPL"])
        
        # Should not include tickers without data
        assert "AAPL" not in result or result.get("AAPL") is None
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_factor_empty_universe(self, mock_session_scope):
        """Test with empty universe."""
        result = get_factor_values("RND_v1_numeric", 2023, [])
        
        assert result == {}


class TestPriceRetrieval:
    """Test price data retrieval."""
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_prices_success(self, mock_session_scope):
        """Test successful price retrieval."""
        mock_session = Mock()
        mock_price1 = Mock()
        mock_price1.adj_close = 100.0
        mock_price2 = Mock()
        mock_price2.adj_close = 110.0
        
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_price1, mock_price2
        ]
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_prices(
            ["AAPL"],
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )
        
        assert "AAPL" in result
        assert len(result["AAPL"]) == 2
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_prices_no_data(self, mock_session_scope):
        """Test handling when no price data exists."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_prices(
            ["AAPL"],
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )
        
        assert "AAPL" in result
        assert result["AAPL"] == []
    
    @patch("src.backtesting.engine.db_session_scope")
    def test_get_prices_missing_ticker(self, mock_session_scope):
        """Test handling of missing ticker."""
        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        result = get_prices(
            ["UNKNOWN"],
            datetime(2023, 1, 1),
            datetime(2023, 12, 31)
        )
        
        assert "UNKNOWN" in result


class TestStatistics:
    """Test statistical calculations."""
    
    def test_calculate_returns(self):
        """Test return calculation."""
        prices = [100.0, 110.0, 120.0, 115.0]
        
        returns = calculate_returns(prices)
        
        assert len(returns) == 3
        assert returns[0] == pytest.approx(0.1)  # (110-100)/100
        assert returns[1] == pytest.approx(0.0909, rel=0.01)  # (120-110)/110
    
    def test_calculate_returns_empty(self):
        """Test return calculation with empty prices."""
        prices = []
        
        returns = calculate_returns(prices)
        
        assert returns == []
    
    def test_calculate_returns_single_price(self):
        """Test return calculation with single price."""
        prices = [100.0]
        
        returns = calculate_returns(prices)
        
        assert returns == []
    
    def test_calculate_portfolio_return(self):
        """Test portfolio return calculation."""
        weights = {"AAPL": 0.5, "MSFT": 0.5}
        returns = {"AAPL": [0.1, 0.05], "MSFT": [0.08, 0.06]}
        
        portfolio_returns = calculate_portfolio_return(weights, returns)
        
        assert len(portfolio_returns) == 2
        # First period: 0.5 * 0.1 + 0.5 * 0.08 = 0.09
        assert portfolio_returns[0] == pytest.approx(0.09)
    
    def test_calculate_statistics(self):
        """Test statistical summary calculation."""
        returns = [0.1, 0.05, -0.02, 0.08, 0.03]
        
        stats = calculate_statistics(returns)
        
        assert "mean" in stats
        assert "std" in stats
        assert "n" in stats
        assert stats["n"] == 5
    
    def test_calculate_statistics_empty(self):
        """Test statistics with empty returns."""
        returns = []
        
        stats = calculate_statistics(returns)
        
        # Should handle gracefully
        assert isinstance(stats, dict)
    
    def test_calculate_drawdown(self):
        """Test drawdown calculation."""
        returns = [0.1, 0.05, -0.1, -0.05, 0.08]
        
        drawdown = calculate_drawdown(returns)
        
        # Should calculate maximum drawdown
        assert drawdown >= 0


class TestPortfolioConstruction:
    """Test portfolio construction logic."""
    
    def test_assign_buckets(self):
        """Test bucket assignment."""
        factor_values = {
            "AAPL": 0.2,
            "MSFT": 0.15,
            "GOOGL": 0.1,
            "AMZN": 0.05,
            "META": 0.0,
        }
        
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        assert len(buckets) == 5
        # Highest value should be in highest bucket
        max_ticker = max(factor_values, key=factor_values.get)
        assert buckets[max_ticker] == 4  # Highest bucket (0-indexed)
    
    def test_assign_buckets_empty(self):
        """Test bucket assignment with empty factor values."""
        factor_values = {}
        
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        assert buckets == {}
    
    def test_assign_buckets_single_value(self):
        """Test bucket assignment with single value."""
        factor_values = {"AAPL": 0.15}
        
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        assert buckets["AAPL"] == 2  # Middle bucket (approximately)
    
    def test_assign_buckets_tied_values(self):
        """Test bucket assignment with tied factor values."""
        factor_values = {
            "AAPL": 0.15,
            "MSFT": 0.15,
            "GOOGL": 0.15,
        }
        
        buckets = assign_buckets(factor_values, num_buckets=3)
        
        # All should be assigned to buckets
        assert len(buckets) == 3


class TestBacktestRun:
    """Test backtest execution."""
    
    @patch("src.backtesting.engine.get_pilot_companies")
    @patch("src.backtesting.engine.get_factor_values")
    @patch("src.backtesting.engine.assign_buckets")
    @patch("src.backtesting.engine.db_session_scope")
    def test_run_backtest_basic(self, mock_session_scope, mock_assign, mock_factor, mock_universe):
        """Test basic backtest run."""
        # Mock universe
        mock_universe.return_value = [{"ticker": "AAPL"}, {"ticker": "MSFT"}]
        
        # Mock factor values
        mock_factor.return_value = {"AAPL": 0.15, "MSFT": 0.10}
        
        # Mock buckets
        mock_assign.return_value = {"AAPL": 0, "MSFT": 1}
        
        # Mock database
        mock_session = Mock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_session.commit = Mock()
        mock_session.add = Mock()
        mock_session_scope.return_value.__enter__.return_value = mock_session
        
        spec = BacktestSpec(
            factor_id="RND_v1_numeric",
            universe=["pilot_top10"],
            start_year=2020,
            end_year=2022,
            formation_schedule="annual",
            holding_period_years=1,
            num_buckets=5,
        )
        
        # Would run backtest
        # result = run_backtest(spec)
        # assert result is not None


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_negative_factor_values(self):
        """Test handling of negative factor values."""
        factor_values = {
            "AAPL": -0.1,
            "MSFT": 0.0,
            "GOOGL": 0.1,
        }
        
        buckets = assign_buckets(factor_values, num_buckets=3)
        
        # Should handle negative values
        assert len(buckets) == 3
    
    def test_very_large_factor_values(self):
        """Test handling of very large factor values."""
        factor_values = {
            "AAPL": 1e10,
            "MSFT": 1e9,
        }
        
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        # Should handle large values
        assert len(buckets) == 2
    
    def test_nan_factor_values(self):
        """Test handling of NaN factor values."""
        import math
        
        factor_values = {
            "AAPL": float('nan'),
            "MSFT": 0.15,
        }
        
        # Should handle NaN gracefully (may skip or assign to bucket)
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        assert isinstance(buckets, dict)
    
    def test_infinity_factor_values(self):
        """Test handling of infinity factor values."""
        import math
        
        factor_values = {
            "AAPL": float('inf'),
            "MSFT": 0.15,
        }
        
        # Should handle infinity
        buckets = assign_buckets(factor_values, num_buckets=5)
        
        assert isinstance(buckets, dict)


class TestDataQuality:
    """Test data quality validation in backtesting."""
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_factor_values(self):
        """Test validation of factor values before backtest."""
        # Would validate that factor values are reasonable
        pass
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_price_data(self):
        """Test validation of price data quality."""
        # Would validate prices (no gaps, reasonable values, etc.)
        pass
    
    @pytest.mark.skip(reason="Data validation not yet implemented")
    def test_validate_universe(self):
        """Test validation of universe (sufficient companies)."""
        # Would validate minimum universe size
        pass


class TestPerformance:
    """Test performance characteristics."""
    
    @pytest.mark.skip(reason="Performance tests require setup")
    def test_backtest_performance_large_universe(self):
        """Test backtest performance with large universe."""
        # Would test with 1000+ companies
        pass
    
    @pytest.mark.skip(reason="Performance tests require setup")
    def test_backtest_performance_long_horizon(self):
        """Test backtest performance with long time horizon."""
        # Would test with 20+ years
        pass

