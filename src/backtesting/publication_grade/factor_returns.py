# PATH: src/backtesting/publication_grade/factor_returns.py
# PURPOSE:
#   - Build R&D factor return series
#   - Fama-French factor regression (alpha decomposition)
#   - Factor loading analysis
#
# ROLE IN ARCHITECTURE:
#   - Factor analysis layer for publication-grade research
#
# METHODOLOGY:
#   - Download/load FF3/FF5 factor returns
#   - Regress R&D factor returns on FF factors
#   - Report alpha with HAC standard errors
#
# NOTES FOR FUTURE AI:
#   - Factor data should be aligned by date
#   - All returns must be in same units (decimal or %)
#   - Use monthly data for regression if possible

import logging
from datetime import date, datetime
from typing import List, Dict, Optional, Tuple
import numpy as np

from .schemas import FactorPremiumSeries

logger = logging.getLogger(__name__)


class FactorReturnSeries:
    """
    Factor return series and Fama-French regression analysis.
    
    Key capabilities:
    1. Build R&D factor return series (Q5-Q1)
    2. Load Fama-French factor data
    3. Run factor regression with HAC errors
    4. Decompose alpha vs factor exposures
    """
    
    # Kenneth French data library base URL
    FF_DATA_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    
    def __init__(self, rd_premium_series: Optional[FactorPremiumSeries] = None):
        """
        Initialize with R&D factor return series.
        
        Args:
            rd_premium_series: Q5-Q1 return series from PortfolioEngine
        """
        self.rd_series = rd_premium_series
        self.ff_factors = None
        
    def load_fama_french_factors(
        self,
        factor_model: str = "FF3"
    ) -> Dict[str, List[float]]:
        """
        Load Fama-French factor returns.
        
        Args:
            factor_model: "FF3" (MKT, SMB, HML) or "FF5" (adds RMW, CMA)
            
        Returns:
            Dict with factor returns by date
        """
        logger.info(f"Loading {factor_model} factors...")
        
        # For now, return placeholder structure
        # In production, download from Kenneth French data library
        
        # TODO: Implement actual data download
        # Files:
        # - F-F_Research_Data_Factors.CSV (FF3 monthly)
        # - F-F_Research_Data_5_Factors_2x3.CSV (FF5 monthly)
        
        self.ff_factors = {
            "MKT_RF": [],  # Market excess return
            "SMB": [],     # Small minus Big
            "HML": [],     # High minus Low (value)
            "RF": [],      # Risk-free rate
        }
        
        if factor_model == "FF5":
            self.ff_factors["RMW"] = []  # Robust minus Weak (profitability)
            self.ff_factors["CMA"] = []  # Conservative minus Aggressive (investment)
        
        logger.warning("FF factor loading not fully implemented - using placeholders")
        
        return self.ff_factors
    
    def run_factor_regression(
        self,
        use_hac: bool = True,
        n_lags: Optional[int] = None
    ) -> Dict:
        """
        Regress R&D factor returns on Fama-French factors.
        
        Model: R_RD,t = α + β_mkt * MKT_t + β_smb * SMB_t + β_hml * HML_t + ε_t
        
        Args:
            use_hac: Use Newey-West HAC standard errors
            n_lags: Number of lags for HAC (auto-select if None)
            
        Returns:
            Dict with alpha, betas, t-stats, R-squared
        """
        if not self.rd_series or not self.rd_series.premiums:
            return {"error": "No R&D factor return series available"}
        
        if not self.ff_factors:
            self.load_fama_french_factors()
        
        # For now, return structure showing what would be computed
        # In production, use statsmodels OLS with HAC
        
        try:
            import statsmodels.api as sm
            from statsmodels.regression.linear_model import OLS
            
            # Build regression matrices
            # Y = R&D factor returns
            # X = FF factors + constant
            
            # Placeholder implementation
            result = {
                "alpha": 0.0,
                "alpha_tstat": 0.0,
                "alpha_pvalue": 1.0,
                "betas": {
                    "MKT_RF": 0.0,
                    "SMB": 0.0,
                    "HML": 0.0,
                },
                "rsquared": 0.0,
                "n_observations": len(self.rd_series.premiums),
                "hac_used": use_hac,
                "warning": "Full FF regression requires aligned factor data"
            }
            
        except ImportError:
            result = {
                "error": "statsmodels not installed",
                "n_observations": len(self.rd_series.premiums)
            }
        
        return result
    
    def compute_factor_loadings(
        self,
        quintile_returns: Dict[int, List[float]]
    ) -> Dict[int, Dict[str, float]]:
        """
        Compute factor loadings for each quintile.
        
        Useful for understanding WHY quintile returns differ.
        E.g., do high R&D stocks have higher market beta?
        """
        loadings = {}
        
        for q, returns in quintile_returns.items():
            # Would run regression for each quintile
            loadings[q] = {
                "MKT_RF_beta": 0.0,
                "SMB_beta": 0.0,
                "HML_beta": 0.0,
                "alpha": 0.0,
            }
        
        return loadings
    
    def decompose_premium(self) -> Dict:
        """
        Decompose R&D premium into:
        1. Alpha (unexplained by factors)
        2. Factor exposures (explained by MKT, SMB, HML, etc.)
        
        This addresses the question: "Is the R&D premium real alpha,
        or is it just exposure to known risk factors?"
        """
        if not self.rd_series:
            return {"error": "No R&D series loaded"}
        
        regression_result = self.run_factor_regression()
        
        # Decomposition
        raw_premium = np.mean(self.rd_series.premiums) if self.rd_series.premiums else 0
        
        decomposition = {
            "raw_premium": raw_premium,
            "alpha_component": regression_result.get("alpha", 0),
            "factor_components": {},
            "explained_pct": 0.0,
            "unexplained_pct": 100.0,
        }
        
        # Factor contributions = beta * factor_mean
        if self.ff_factors and "betas" in regression_result:
            for factor, beta in regression_result["betas"].items():
                if factor in self.ff_factors and self.ff_factors[factor]:
                    factor_mean = np.mean(self.ff_factors[factor])
                    contribution = beta * factor_mean
                    decomposition["factor_components"][factor] = contribution
        
        return decomposition

