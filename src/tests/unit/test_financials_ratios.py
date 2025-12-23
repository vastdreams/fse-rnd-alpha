"""Unit tests for financial ratios calculation."""
import pytest
from src.financials.ratios import calculate_ratios
from src.financials.canonical_schema import IncomeStatement, BalanceSheet, CashFlowStatement


def test_calculate_ratios_basic():
    """Test basic ratio calculations."""
    income = IncomeStatement(
        revenue=1000000,
        cost_of_revenue=600000,
        operating_expenses=200000,
        net_income=200000,
    )
    balance = BalanceSheet(
        total_assets=5000000,
        total_liabilities=2000000,
        total_equity=3000000,
    )
    cashflow = CashFlowStatement(
        operating_cash_flow=250000,
        capital_expenditures=-50000,
    )
    
    ratios = calculate_ratios(income, balance, cashflow)
    
    assert ratios.gross_margin == pytest.approx(0.4, rel=0.01)  # 40%
    assert ratios.net_margin == pytest.approx(0.2, rel=0.01)  # 20%
    assert ratios.debt_to_equity == pytest.approx(0.667, rel=0.01)  # 2M/3M


def test_calculate_ratios_rd_intensity():
    """Test R&D intensity calculation."""
    income = IncomeStatement(
        revenue=1000000,
        rd_expense=100000,
    )
    balance = BalanceSheet()
    cashflow = CashFlowStatement()
    
    ratios = calculate_ratios(income, balance, cashflow)
    
    assert ratios.rd_intensity == pytest.approx(0.1, rel=0.01)  # 10%


def test_calculate_ratios_with_none():
    """Test ratio calculation handles None values."""
    income = IncomeStatement(revenue=1000000)
    balance = BalanceSheet()
    cashflow = CashFlowStatement()
    
    ratios = calculate_ratios(income, balance, cashflow)
    
    # Should not crash, ratios may be None
    assert ratios is not None

