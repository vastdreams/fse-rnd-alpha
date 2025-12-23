"""Canonical financial schema definitions."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomeStatement:
    """Canonical Income Statement fields."""
    revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    rd_expense: Optional[float] = None
    sga_expense: Optional[float] = None
    operating_income: Optional[float] = None
    ebit: Optional[float] = None
    interest_expense: Optional[float] = None
    pretax_income: Optional[float] = None
    income_tax: Optional[float] = None
    net_income: Optional[float] = None
    eps_basic: Optional[float] = None
    eps_diluted: Optional[float] = None


@dataclass
class BalanceSheet:
    """Canonical Balance Sheet fields."""
    total_assets: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    short_term_investments: Optional[float] = None
    accounts_receivable: Optional[float] = None
    inventory: Optional[float] = None
    ppe_net: Optional[float] = None
    goodwill: Optional[float] = None
    intangible_assets: Optional[float] = None
    total_liabilities: Optional[float] = None
    short_term_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    total_equity: Optional[float] = None
    retained_earnings: Optional[float] = None


@dataclass
class CashFlowStatement:
    """Canonical Cash Flow Statement fields."""
    cash_from_operations: Optional[float] = None
    cash_from_investing: Optional[float] = None
    cash_from_financing: Optional[float] = None
    capex: Optional[float] = None
    depreciation_amortization: Optional[float] = None
    dividends_paid: Optional[float] = None
    share_repurchases: Optional[float] = None


@dataclass
class FinancialStatements:
    """Complete financial statements."""
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlowStatement

