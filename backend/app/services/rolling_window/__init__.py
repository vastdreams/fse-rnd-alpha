"""
PATH: backend/app/services/rolling_window/__init__.py
PURPOSE:
  - Analyze R&D-return relationships across rolling windows
  - Build quintile portfolios based on R&D intensity
  - Compute forward returns for each quintile

METHODOLOGY NOTE:
  - Uses FY(T-1) data to form portfolios at start of year T
  - R&D intensity capped at 100% (200% for biotech/healthcare) to prevent outliers
  - Minimum revenue filter ($100M) to exclude pre-revenue companies
  - Zero-R&D companies included in Q1 (lowest R&D intensity)

LOOK-AHEAD BIAS CONSIDERATIONS:
  - Fiscal year-end data (FY T-1) is not available until the 10-K filing
  - Most 10-K filings occur within 60-90 days after fiscal year-end
  - For calendar-year companies, FY 2009 data is filed by March 2010
  - CALENDAR year returns (Jan-Dec) can have slight look-ahead bias when using FY(T-1) data
    because FY(T-1) is not fully public on Jan 1 of year T for many firms.
  - This service defaults to July-June returns (Fama-French convention) via `JulyJuneReturn`
    when `use_july_june=True` (default). This is the publication-grade, bias-minimized path.

KNOWN LIMITATIONS:
  1. Survivorship bias: Uses current S&P 500 constituents (unless historical data loaded)
  2. Filing date timing: ~3 month lag not perfectly handled with annual data
  3. Overlapping windows: Rolling windows are not independent observations

MODULE STRUCTURE:
  _models.py          — QuintileResult dataclass
  _base.py            — RollingWindowBase (init, risk-free rate, eligible companies, quintile assignment)
  _calculator.py      — CalculatorMixin (quintile stats, single/all window computation)
  _factor_premiums.py — FactorPremiumsMixin (annual R&D factor premiums)
  _query.py           — QueryMixin (stored results retrieval, aggregation, weighted returns)
  _robustness.py      — RobustnessMixin (sector-neutral premium, EW vs VW comparison)
  _sensitivity.py     — SensitivityMixin (R&D cap sensitivity analysis)
"""

from ._models import QuintileResult
from ._base import RollingWindowBase
from ._calculator import CalculatorMixin
from ._factor_premiums import FactorPremiumsMixin
from ._query import QueryMixin
from ._robustness import RobustnessMixin
from ._sensitivity import SensitivityMixin


class RollingWindowAnalyzer(
    CalculatorMixin,
    FactorPremiumsMixin,
    QueryMixin,
    RobustnessMixin,
    SensitivityMixin,
    RollingWindowBase,
):
    """
    Analyze R&D-return relationships across rolling windows.

    Composed from mixins:
    - RollingWindowBase: init, risk-free rates, eligible companies, quintile assignment
    - CalculatorMixin: quintile stats, single/batch window computation
    - FactorPremiumsMixin: annual R&D factor premium (Q5 - Q1)
    - QueryMixin: retrieve/aggregate stored results, weighted returns
    - RobustnessMixin: sector-neutral premium, EW vs VW comparison
    - SensitivityMixin: R&D cap sensitivity analysis
    """
    pass


__all__ = ["RollingWindowAnalyzer", "QuintileResult"]
