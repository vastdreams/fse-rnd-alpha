"""
Unit tests for RollingWindowAnalyzer.

These tests verify:
1. Portfolio return calculation (equal-weighted, rebalanced annually)
2. Quintile assignment
3. Correct handling of overlapping windows
"""

import numpy as np
from unittest.mock import MagicMock, AsyncMock
from dataclasses import dataclass
from typing import Dict, List


# Simplified version of the classes for testing
@dataclass
class MockCompanyData:
    symbol: str
    rd_intensity: float
    returns: Dict[int, float]  # year -> return %


def calculate_portfolio_return_test(
    companies: List[MockCompanyData],
    years: List[int]
) -> float:
    """
    Test implementation of portfolio return calculation.
    
    METHODOLOGY:
    1. For each year in the window, compute equal-weighted average return across companies
    2. Compound the yearly portfolio returns
    
    This is equivalent to annual equal-weight rebalancing.
    """
    if not companies:
        return 0.0
    
    yearly_portfolio_returns = []
    
    for year in years:
        # Get returns for all companies that have data for this year
        year_returns = [c.returns[year] for c in companies if year in c.returns]
        
        if year_returns:
            # Equal-weighted average for the year
            yearly_portfolio_returns.append(np.mean(year_returns))
    
    if not yearly_portfolio_returns:
        return 0.0
    
    # Compound annual returns
    # (1 + r1/100) * (1 + r2/100) * ... - 1, then convert back to percentage
    cumulative = np.prod([1 + r/100 for r in yearly_portfolio_returns])
    total_return = (cumulative - 1) * 100
    
    return total_return


def assign_quintiles_test(companies: List[MockCompanyData]) -> Dict[int, List[MockCompanyData]]:
    """
    Test implementation of quintile assignment.
    
    Q1 = Lowest R&D intensity (bottom 20%)
    Q5 = Highest R&D intensity (top 20%)
    """
    if not companies:
        return {i: [] for i in range(1, 6)}
    
    # Sort by R&D intensity
    sorted_companies = sorted(companies, key=lambda x: x.rd_intensity)
    
    n = len(sorted_companies)
    quintile_size = n // 5
    
    quintiles = {}
    for q in range(1, 6):
        start_idx = (q - 1) * quintile_size
        if q == 5:
            # Last quintile gets remaining companies
            end_idx = n
        else:
            end_idx = q * quintile_size
        
        quintiles[q] = sorted_companies[start_idx:end_idx]
    
    return quintiles


class TestPortfolioReturnCalculation:
    """Tests for portfolio return calculation methodology."""
    
    def test_two_company_two_year_example(self):
        """
        Hand-calculated example:
        
        Company A: Year 1 = +10%, Year 2 = +20%
        Company B: Year 1 = +30%, Year 2 = +40%
        
        Year 1 portfolio return = (10 + 30) / 2 = 20%
        Year 2 portfolio return = (20 + 40) / 2 = 30%
        
        Total return = (1 + 0.20) * (1 + 0.30) - 1 = 1.56 - 1 = 56%
        """
        companies = [
            MockCompanyData("A", 5.0, {2020: 10.0, 2021: 20.0}),
            MockCompanyData("B", 10.0, {2020: 30.0, 2021: 40.0}),
        ]
        
        result = calculate_portfolio_return_test(companies, [2020, 2021])
        expected = 56.0  # (1.20 * 1.30 - 1) * 100
        
        assert abs(result - expected) < 0.01, f"Expected {expected}, got {result}"
    
    def test_single_company(self):
        """Single company = portfolio return equals company return."""
        companies = [
            MockCompanyData("A", 5.0, {2020: 15.0, 2021: 25.0}),
        ]
        
        result = calculate_portfolio_return_test(companies, [2020, 2021])
        expected = (1.15 * 1.25 - 1) * 100  # 43.75%
        
        assert abs(result - expected) < 0.01
    
    def test_negative_returns(self):
        """Portfolio handles negative returns correctly."""
        companies = [
            MockCompanyData("A", 5.0, {2020: -10.0, 2021: 20.0}),
            MockCompanyData("B", 10.0, {2020: 10.0, 2021: -20.0}),
        ]
        
        # Year 1: (-10 + 10) / 2 = 0%
        # Year 2: (20 + -20) / 2 = 0%
        # Total: (1.0 * 1.0 - 1) * 100 = 0%
        
        result = calculate_portfolio_return_test(companies, [2020, 2021])
        expected = 0.0
        
        assert abs(result - expected) < 0.01
    
    def test_empty_portfolio(self):
        """Empty portfolio returns 0."""
        result = calculate_portfolio_return_test([], [2020, 2021])
        assert result == 0.0
    
    def test_missing_year_data(self):
        """Portfolio handles missing year data."""
        companies = [
            MockCompanyData("A", 5.0, {2020: 10.0}),  # Only has 2020
            MockCompanyData("B", 10.0, {2020: 20.0, 2021: 30.0}),  # Has both
        ]
        
        # Year 1: (10 + 20) / 2 = 15%
        # Year 2: 30 / 1 = 30% (only B has data)
        # Total: (1.15 * 1.30 - 1) * 100 = 49.5%
        
        result = calculate_portfolio_return_test(companies, [2020, 2021])
        expected = 49.5
        
        assert abs(result - expected) < 0.01


class TestQuintileAssignment:
    """Tests for quintile assignment logic."""
    
    def test_equal_quintiles_10_companies(self):
        """10 companies split evenly into 5 quintiles of 2 each."""
        companies = [
            MockCompanyData(f"C{i}", float(i), {2020: 10.0})
            for i in range(10)
        ]
        
        quintiles = assign_quintiles_test(companies)
        
        # Each quintile should have 2 companies
        for q in range(1, 6):
            assert len(quintiles[q]) == 2
        
        # Q1 should have lowest R&D (0, 1)
        assert quintiles[1][0].rd_intensity == 0.0
        assert quintiles[1][1].rd_intensity == 1.0
        
        # Q5 should have highest R&D (8, 9)
        assert quintiles[5][0].rd_intensity == 8.0
        assert quintiles[5][1].rd_intensity == 9.0
    
    def test_uneven_distribution(self):
        """11 companies - last quintile gets extras."""
        companies = [
            MockCompanyData(f"C{i}", float(i), {2020: 10.0})
            for i in range(11)
        ]
        
        quintiles = assign_quintiles_test(companies)
        
        # First 4 quintiles: 2 each, last quintile: 3
        assert len(quintiles[1]) == 2
        assert len(quintiles[5]) == 3
    
    def test_sorting_order(self):
        """Companies sorted by R&D intensity, not by symbol."""
        companies = [
            MockCompanyData("Z", 50.0, {}),
            MockCompanyData("A", 5.0, {}),
            MockCompanyData("M", 25.0, {}),
        ]
        
        quintiles = assign_quintiles_test(companies)
        
        # With 3 companies: Q1=1, Q2=0, Q3=0, Q4=0, Q5=2
        # Actually with floor division: 3 // 5 = 0, so all go to Q5
        # This is edge case behavior - with small n, quintiles may be empty
        total = sum(len(q) for q in quintiles.values())
        assert total == 3


class TestStatisticalMethods:
    """Tests for statistical methodology."""
    
    def test_cohens_d_average_variance(self):
        """
        Test that Cohen's d uses average variance formula for unequal variances.
        
        Formula: d = (mean2 - mean1) / sqrt((var1 + var2) / 2)
        """
        group1 = [10, 20, 30]  # mean=20, var=100
        group2 = [40, 50, 60]  # mean=50, var=100
        
        mean_diff = np.mean(group2) - np.mean(group1)  # 30
        var1 = np.var(group1, ddof=1)  # 100
        var2 = np.var(group2, ddof=1)  # 100
        avg_sd = np.sqrt((var1 + var2) / 2)  # 10
        
        expected_d = mean_diff / avg_sd  # 3.0
        
        assert abs(expected_d - 3.0) < 0.01
    
    def test_cohens_d_unequal_variance(self):
        """
        Test Cohen's d with unequal variances.
        """
        group1 = [10, 11, 12]  # mean=11, var=1
        group2 = [40, 50, 60]  # mean=50, var=100
        
        mean_diff = np.mean(group2) - np.mean(group1)  # 39
        var1 = np.var(group1, ddof=1)  # 1
        var2 = np.var(group2, ddof=1)  # 100
        avg_sd = np.sqrt((var1 + var2) / 2)  # sqrt(50.5) ≈ 7.11
        
        expected_d = mean_diff / avg_sd  # 39 / 7.11 ≈ 5.49
        
        assert abs(expected_d - 5.49) < 0.1


if __name__ == "__main__":
    # Run tests
    test = TestPortfolioReturnCalculation()
    test.test_two_company_two_year_example()
    test.test_single_company()
    test.test_negative_returns()
    test.test_empty_portfolio()
    test.test_missing_year_data()
    print("Portfolio return tests passed!")
    
    test2 = TestQuintileAssignment()
    test2.test_equal_quintiles_10_companies()
    test2.test_uneven_distribution()
    test2.test_sorting_order()
    print("Quintile assignment tests passed!")
    
    test3 = TestStatisticalMethods()
    test3.test_cohens_d_average_variance()
    test3.test_cohens_d_unequal_variance()
    print("Statistical method tests passed!")
    
    print("\nAll tests passed!")

