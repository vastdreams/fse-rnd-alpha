"""
PATH: backend/app/services/rd_alpha_scorer/constraints_mixin.py
PURPOSE: Mixin providing sector constraint application and methodology documentation.
WHY: Keeps sector-constraint logic separate from per-company scoring and top-level orchestrator.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from app.services.rd_alpha_scorer.data_classes import (
    RDAlphaScore,
    SectorWeight,
    SelectionMethodology,
    SP500_SECTOR_WEIGHTS,
)
from app.services.etf_universe import EligibilityResult


class ConstraintsMixin:
    """
    Mixin that provides sector-constraint and methodology methods.

    Expects the consumer class to define:
        MAX_SECTOR_WEIGHT, MIN_SECTOR_WEIGHT, MIN_COMPANIES_PER_SECTOR,
        VOLATILITY_FLOOR, MIN_MOMENTUM_FACTOR, MAX_MOMENTUM_FACTOR: class attrs
    """

    async def apply_sector_constraints(
        self,
        scores: List[RDAlphaScore],
        n_holdings: int = 20
    ) -> Tuple[List[RDAlphaScore], List[SectorWeight]]:
        """
        Apply sector diversification constraints to selection.

        Ensures no single sector exceeds MAX_SECTOR_WEIGHT and
        attempts to include representation from multiple sectors.

        Returns:
            Tuple of (selected holdings, sector weight breakdown)
        """
        if not scores:
            return [], []

        # Calculate target sector weights
        sectors_in_universe = set(s.sector for s in scores)
        target_weights = {}

        for sector in sectors_in_universe:
            sp500_weight = SP500_SECTOR_WEIGHTS.get(sector, 0.05)
            target = min(sp500_weight * 1.5, self.MAX_SECTOR_WEIGHT)
            target_weights[sector] = {
                "target": target,
                "min": max(sp500_weight * 0.5, self.MIN_SECTOR_WEIGHT),
                "max": self.MAX_SECTOR_WEIGHT,
            }

        # Select companies with sector constraints
        selected = []
        sector_counts = {}
        sector_scores = {}

        for score in scores:
            sector = score.sector
            current_count = sector_counts.get(sector, 0)

            # Calculate how much weight this sector already has
            current_weight = current_count / n_holdings if n_holdings > 0 else 0

            # Check if sector is at max capacity
            if current_weight >= self.MAX_SECTOR_WEIGHT:
                continue

            # Add company
            selected.append(score)
            sector_counts[sector] = current_count + 1
            sector_scores[sector] = sector_scores.get(sector, []) + [score]

            if len(selected) >= n_holdings:
                break

        # Calculate final weights (equal weight within sector constraints)
        total_selected = len(selected)
        for score in selected:
            score.weight = 1.0 / total_selected if total_selected > 0 else 0.0

        # Build sector weight breakdown
        sector_weight_info = []
        for sector in sectors_in_universe:
            count = sector_counts.get(sector, 0)
            actual_weight = count / total_selected if total_selected > 0 else 0
            target_info = target_weights.get(sector, {"target": 0.05, "min": 0.02, "max": 0.25})

            sector_weight_info.append(SectorWeight(
                sector=sector,
                target_weight=target_info["target"],
                actual_weight=actual_weight,
                min_weight=target_info["min"],
                max_weight=target_info["max"],
                company_count=count,
                adjustment_needed=target_info["target"] - actual_weight,
            ))

        # Sort by actual weight descending
        sector_weight_info.sort(key=lambda x: x.actual_weight, reverse=True)

        # Update ranks for selected
        for i, score in enumerate(selected):
            score.selection_rank = i + 1

        return selected, sector_weight_info

    def get_selection_methodology(self) -> SelectionMethodology:
        """
        Return complete documentation of the selection methodology.

        Provides transparency on how companies are selected and weighted.
        """
        return SelectionMethodology(
            formula="R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility",
            formula_latex=r"\text{Score} = \frac{\text{RD}_{\text{cap}} \times \text{Sector}_{\text{adj}} \times \text{Momentum} \times \text{Quality}}{\sigma}",
            components={
                "RD_Intensity": "R&D Expense / Revenue, capped at sector-specific maximum (100% default, 200% for biotech/pharma). From Paper 1.",
                "Sector_Adjustment": "S&P 500 sector weight / High-R&D universe sector weight. Prevents tech/biotech overconcentration. From Paper 2.",
                "Momentum": "1 + (Prior 3-year excess return vs S&P 500 × 0.1). Uses real historical returns. From Paper 3.",
                "Quality": "Data quality score from 0-1. Based on years of data and consistency.",
                "Volatility": "3-year trailing annualized volatility from daily returns, floored at 10%. Uses real price data. From Paper 4.",
            },
            sector_constraints={
                "max_sector_weight": {"value": self.MAX_SECTOR_WEIGHT, "description": "No single sector > 25%"},
                "min_sector_weight": {"value": self.MIN_SECTOR_WEIGHT, "description": "Minimum 2% per included sector"},
                "momentum_bounds": {"value": f"{self.MIN_MOMENTUM_FACTOR}-{self.MAX_MOMENTUM_FACTOR}", "description": "Momentum factor capped between 0.5 and 2.0"},
            },
            research_citations=[
                "Paper 1: R&D intensity as primary alpha factor (Q5 outperforms Q1 by ~10% annually)",
                "Paper 2: Industry patterns - tech/biotech naturally dominate, requiring sector adjustment",
                "Paper 3: Pricing factor - R&D premium persists over time, using real 3-year excess returns",
                "Paper 4: Value Creation - volatility normalization using real 3-year daily price data",
                "Fama-French: July-June return convention for look-ahead bias elimination",
            ],
            parameters={
                "rd_cap_default": 1.0,
                "rd_cap_biotech": 2.0,
                "max_sector_weight": self.MAX_SECTOR_WEIGHT,
                "min_sector_weight": self.MIN_SECTOR_WEIGHT,
                "volatility_floor": self.VOLATILITY_FLOOR,
                "momentum_sensitivity": 0.1,
                "momentum_min": self.MIN_MOMENTUM_FACTOR,
                "momentum_max": self.MAX_MOMENTUM_FACTOR,
            },
            last_updated=datetime.now().strftime("%Y-%m-%d"),
        )

    async def get_all_candidates_with_scores(
        self,
        as_of_year: Optional[int] = None,
        limit: int = 100
    ) -> Tuple[List[RDAlphaScore], Optional[EligibilityResult]]:
        """
        Get all candidate companies with their scores for transparency.

        Returns full list so users can see why companies were/weren't selected.
        """
        scores, eligibility = await self.calculate_alpha_scores(
            universe="sp500",
            as_of_year=as_of_year
        )
        return scores[:limit], eligibility
