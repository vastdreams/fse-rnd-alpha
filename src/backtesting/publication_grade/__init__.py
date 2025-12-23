# PATH: src/backtesting/publication_grade/__init__.py
# PURPOSE: Publication-grade portfolio analysis engine
#
# This module implements methodologically correct portfolio sorts following
# standard asset pricing conventions (e.g., Fama-French methodology).
#
# KEY DESIGN PRINCIPLES:
# 1. Portfolio return TIME SERIES (not cross-sectional averages)
# 2. Annual rebalancing with proper formation timing
# 3. Filing date lag enforcement (July formation convention)
# 4. Proper treatment of zero vs missing R&D
# 5. HAC (Newey-West) standard errors for inference
# 6. No look-ahead bias

from .portfolio_engine import PortfolioEngine
from .factor_returns import FactorReturnSeries
from .inference import NeweyWestInference
from .schemas import (
    FormationPeriod,
    PortfolioReturn,
    QuintileTimeSeries,
    FactorPremiumSeries
)

__all__ = [
    'PortfolioEngine',
    'FactorReturnSeries', 
    'NeweyWestInference',
    'FormationPeriod',
    'PortfolioReturn',
    'QuintileTimeSeries',
    'FactorPremiumSeries'
]

