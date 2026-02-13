# Tier-2 July-June return calculator using CRSP monthly RET/DLRET data.
import logging
import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, text, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JulyJuneReturn, ComputationRun

logger = logging.getLogger(__name__)


class Tier2JulyJuneCalculator:
    """Calculate July-June returns from CRSP monthly RET/DLRET (Tier-2).
    Convention: Formation Year T -> Returns July(T+1) to June(T+2), no look-ahead bias.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.computation_run_id: Optional[str] = None

    async def compute_all_returns(
        self,
        start_year: int = 1990,
        end_year: int = 2024,
        save_results: bool = True
    ) -> List[Dict]:
        """Compute July-June returns for all PERMNOs in CRSP data."""
        if save_results:
            self.computation_run_id = str(uuid.uuid4())
            run = ComputationRun(
                id=self.computation_run_id,
                computation_type="july_june_returns",
                return_convention="july_june",
                data_tier="tier2",
                start_year=start_year,
                end_year=end_year,
                started_at=datetime.utcnow(),
                status="running"
            )
            self.session.add(run)
            await self.session.commit()
        try:
            all_results = []
            for formation_year in range(start_year, end_year + 1):
                logger.info(f"Computing Tier-2 returns for formation year {formation_year}")
                year_results = await self._compute_year_returns(formation_year)
                all_results.extend(year_results)
                if save_results and year_results:
                    await self._save_returns(year_results)
            if save_results and self.computation_run_id:
                await self.session.execute(
                    text("""
                        UPDATE computation_runs
                        SET status = 'completed',
                            completed_at = :now,
                            records_created = :count
                        WHERE id = :run_id
                    """),
                    {"now": datetime.utcnow(), "count": len(all_results), "run_id": self.computation_run_id}
                )
                await self.session.commit()
            logger.info(f"Computed {len(all_results)} Tier-2 July-June returns")
            return all_results
        except Exception as e:
            if save_results and self.computation_run_id:
                await self.session.execute(
                    text("UPDATE computation_runs SET status = 'failed' WHERE id = :run_id"),
                    {"run_id": self.computation_run_id}
                )
                await self.session.commit()
            raise

    async def _compute_year_returns(self, formation_year: int) -> List[Dict]:
        """Compute July-June returns for a single formation year.
        Formation Year T: Returns span July(T+1) to June(T+2).
        """
        start_date = date(formation_year + 1, 7, 1)
        end_date = date(formation_year + 2, 6, 30)
        result = await self.session.execute(
            text("""
                SELECT
                    permno,
                    date,
                    ret,
                    dlret,
                    ticker
                FROM crsp_monthly_stock
                WHERE date >= :start_date
                  AND date <= :end_date
                  AND (ret IS NOT NULL OR dlret IS NOT NULL)
                ORDER BY permno, date
            """),
            {"start_date": start_date, "end_date": end_date}
        )
        rows = result.fetchall()
        if not rows:
            logger.warning(f"No CRSP data for formation year {formation_year}")
            return []
        permno_data: Dict[int, List[Tuple]] = {}
        permno_tickers: Dict[int, str] = {}
        for row in rows:
            permno = row[0]
            if permno not in permno_data:
                permno_data[permno] = []
            permno_data[permno].append((row[1], row[2], row[3]))  # date, ret, dlret
            if row[4]:
                permno_tickers[permno] = row[4]
        results = []
        for permno, monthly_data in permno_data.items():
            ret_info = self._compound_monthly_returns(monthly_data)
            if ret_info is None:
                continue
            ticker = permno_tickers.get(permno, f"PERMNO_{permno}")
            results.append({
                "symbol": ticker,
                "permno": permno,
                "formation_year": formation_year,
                "data_tier": "tier2",
                "total_return": ret_info["total_return"],
                "annualized_return": ret_info["annualized_return"],
                "volatility": ret_info["volatility"],
                "trading_days": ret_info["n_months"],  # Actually months for Tier-2
                "computation_run_id": self.computation_run_id,
            })
        return results

    def _compound_monthly_returns(self, monthly_data: List[Tuple]) -> Optional[Dict]:
        """Compound monthly returns with delisting return integration.
        CRSP: (1+RET)*(1+DLRET)-1 when both present, else whichever is available.
        """
        if not monthly_data:
            return None
        monthly_returns = []
        for dt, ret, dlret in monthly_data:
            if ret is not None and dlret is not None:
                combined = (1 + ret) * (1 + dlret) - 1
            elif ret is not None:
                combined = ret
            elif dlret is not None:
                combined = dlret
            else:
                continue
            if not np.isnan(combined) and not np.isinf(combined):
                monthly_returns.append(combined)
        if len(monthly_returns) < 6:  # Require at least 6 months
            return None
        compound = 1.0
        for r in monthly_returns:
            compound *= (1 + r)
        total_return = compound - 1
        n_months = len(monthly_returns)
        annualized_return = (compound ** (12 / n_months)) - 1 if n_months > 0 else 0
        if len(monthly_returns) > 1:
            volatility = float(np.std(monthly_returns, ddof=1)) * np.sqrt(12)
        else:
            volatility = 0.0
        return {
            "total_return": float(total_return),
            "annualized_return": float(annualized_return),
            "volatility": float(volatility),
            "n_months": n_months,
        }

    async def _save_returns(self, returns: List[Dict]) -> int:
        """Save computed returns to database."""
        if not returns:
            return 0
        saved = 0
        for ret in returns:
            try:
                await self.session.execute(
                    text("""
                        INSERT INTO july_june_returns
                            (symbol, formation_year, data_tier, permno,
                             total_return, annualized_return, volatility,
                             trading_days, computation_run_id, created_at)
                        VALUES
                            (:symbol, :formation_year, :data_tier, :permno,
                             :total_return, :annualized_return, :volatility,
                             :trading_days, :computation_run_id, :created_at)
                        ON CONFLICT (symbol, formation_year, data_tier) DO UPDATE SET
                            permno = EXCLUDED.permno,
                            total_return = EXCLUDED.total_return,
                            annualized_return = EXCLUDED.annualized_return,
                            volatility = EXCLUDED.volatility,
                            trading_days = EXCLUDED.trading_days,
                            computation_run_id = EXCLUDED.computation_run_id,
                            created_at = EXCLUDED.created_at
                    """),
                    {
                        **ret,
                        "created_at": datetime.utcnow(),
                    }
                )
                saved += 1
            except Exception as e:
                logger.warning(f"Failed to save return for {ret.get('symbol')}: {e}")
        await self.session.commit()
        return saved

    async def get_permno_ticker_map(self) -> Dict[int, str]:
        """Get mapping from PERMNO to most recent ticker."""
        result = await self.session.execute(
            text("""
                SELECT DISTINCT ON (permno) permno, ticker
                FROM crsp_monthly_stock
                WHERE ticker IS NOT NULL
                ORDER BY permno, date DESC
            """)
        )
        return {row[0]: row[1] for row in result.fetchall()}

    async def link_to_compustat(self) -> Dict[int, str]:
        """Get PERMNO to GVKEY mapping from CCM link table."""
        result = await self.session.execute(
            text("""
                SELECT permno, gvkey
                FROM crsp_compustat_link
                WHERE linkprim IN ('P', 'C')
                  AND linktype IN ('LU', 'LC', 'LS')
            """)
        )
        return {row[0]: row[1] for row in result.fetchall()}
