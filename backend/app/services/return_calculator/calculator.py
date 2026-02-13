# JulyJuneReturnCalculator: computes July-June returns per Fama-French convention.
from typing import Optional, Dict, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.return_calculator.constants import PRICE_MODE_TOTAL_RETURN_DIVIDENDS
from app.services.return_calculator._compute import ComputeMixin
from app.services.return_calculator._persistence import PersistenceMixin


class JulyJuneReturnCalculator(ComputeMixin, PersistenceMixin):
    """Computes July-June returns per Fama-French convention.

    Timeline Example:
    - FY 2019 ends Dec 31, 2019
    - 10-K filed by March 2020
    - Portfolio formed July 1, 2020 (formation_year = 2019)
    - Returns measured July 1, 2020 - June 30, 2021

    This ensures no look-ahead bias: when forming portfolios in July 2020,
    we only use FY 2019 data which was publicly available by March 2020.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        data_tier: str = "tier1",
        price_mode: str = PRICE_MODE_TOTAL_RETURN_DIVIDENDS,
    ):
        self.session = session
        self.data_tier = data_tier
        self.price_mode = price_mode
        self._removed_dates_by_symbol: Optional[Dict[str, List[date]]] = None
