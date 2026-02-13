# EXEMPTION: 391 lines — Pure declarative data registry (no logic); splitting would fragment the formula lookup table
"""
PATH: backend/app/core/formulas/registry.py
PURPOSE: Central registry of all mathematical formulas used in the research
WHY: Single source of truth for formula definitions, referenced by all services
FLOW:
  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐
  │ FormulaSpec  │ →  │ FORMULA_REGISTRY │ →  │ Validation/API   │
  └──────────────┘    └──────────────────┘    └──────────────────┘
DEPENDENCIES:
  - spec.py: FormulaSpec dataclass
"""

from typing import Dict

from app.core.formulas.spec import FormulaSpec


# ==============================================================================
# Formula Registry
# ==============================================================================

FORMULA_REGISTRY: Dict[str, FormulaSpec] = {
    
    # --------------------------------------------------------------------------
    # Paper 1: R&D Investment Intensity
    # --------------------------------------------------------------------------
    
    "rd_intensity": FormulaSpec(
        name="R&D Intensity",
        latex=r"\text{RD\_Intensity} = \frac{\text{R\&D Expense}}{\text{Revenue}} \times 100",
        description="Primary research factor measuring R&D investment relative to company size",
        inputs={
            "rd_expense": "R&D expenses from income statement ($)",
            "revenue": "Total revenue from income statement ($)",
        },
        output="R&D intensity as percentage",
        derivation_steps=[
            "1. Extract R&D expense from XBRL/SEC filings (researchAndDevelopmentExpenses)",
            "2. Extract revenue from income statement (totalRevenue or revenue)",
            "3. Validate: revenue > $100M minimum threshold",
            "4. Compute ratio: rd_expense / revenue",
            "5. Convert to percentage: ratio * 100",
            "6. Apply sector-specific cap (100% default, 200% for biotech/pharma)",
        ],
        paper_reference="Paper 1: R&D Investment Intensity and Stock Returns",
        valid_range=(0.0, 200.0),
        unit="%",
        notes=[
            "High R&D sectors (biotech) can legitimately exceed 100%",
            "Values > 200% typically indicate data quality issues",
            "Revenue threshold of $100M excludes micro-caps",
        ]
    ),
    
    "rd_intensity_capped": FormulaSpec(
        name="Capped R&D Intensity",
        latex=r"\text{RD\_Capped} = \min(\text{RD\_Intensity}, \text{Sector\_Cap})",
        description="R&D intensity with sector-specific caps to limit outlier influence",
        inputs={
            "rd_intensity": "Raw R&D intensity (%)",
            "sector": "Company GICS sector classification",
            "sector_cap": "Maximum allowed intensity for sector (%)",
        },
        output="Capped R&D intensity",
        derivation_steps=[
            "1. Look up sector cap: Healthcare/Biotech = 200%, Others = 100%",
            "2. Apply cap: min(rd_intensity, sector_cap)",
        ],
        paper_reference="Paper 1: R&D Investment Intensity and Stock Returns",
        valid_range=(0.0, 200.0),
        unit="%",
    ),
    
    # --------------------------------------------------------------------------
    # Paper 2: Industry Analysis & Sector Adjustment
    # --------------------------------------------------------------------------
    
    "sector_adjustment": FormulaSpec(
        name="Sector Adjustment Factor",
        latex=r"\text{Sector\_Adj} = \frac{\text{Target\_Weight}}{\text{Raw\_Weight}}",
        description="Adjustment factor to achieve sector-agnostic portfolio weights",
        inputs={
            "target_weight": "Target sector weight based on S&P 500 composition (%)",
            "raw_weight": "Raw sector weight from pure R&D ranking (%)",
        },
        output="Multiplier to adjust company scores",
        derivation_steps=[
            "1. Compute raw sector weights from R&D ranking",
            "2. Get target weights from S&P 500 GICS composition",
            "3. Compute adjustment: target / raw (capped at [0.5, 2.0])",
            "4. Apply adjustment to company scores within sector",
        ],
        paper_reference="Paper 2: R&D Industry Analysis",
        valid_range=(0.5, 2.0),
        unit="multiplier",
        notes=[
            "Prevents natural overweighting of tech/biotech",
            "Adjustment capped to prevent extreme distortions",
        ]
    ),
    
    # --------------------------------------------------------------------------
    # Paper 3: Multi-Factor Model & Momentum
    # --------------------------------------------------------------------------
    
    "momentum_factor": FormulaSpec(
        name="Momentum Factor",
        latex=r"\text{Momentum} = \frac{R_{i,t-3:t-1} - R_{m,t-3:t-1}}{\sigma_i}",
        description="3-year excess return normalized by volatility",
        inputs={
            "company_return_3yr": "Company cumulative return over prior 3 years",
            "market_return_3yr": "S&P 500 cumulative return over same period",
            "volatility": "Company annualized volatility",
        },
        output="Standardized momentum score",
        derivation_steps=[
            "1. Compute 3-year cumulative return for company",
            "2. Compute 3-year cumulative return for S&P 500",
            "3. Calculate excess return: company - market",
            "4. Normalize by volatility for comparability",
            "5. Cap at [-2, +2] to limit extreme values",
        ],
        paper_reference="Paper 3: Multi-Factor Integration of R&D Premium",
        valid_range=(-2.0, 2.0),
        unit="std devs",
        notes=[
            "Based on Carhart momentum factor research",
            "Uses July-June returns following Fama-French convention",
        ]
    ),
    
    "excess_return_3yr": FormulaSpec(
        name="3-Year Excess Return",
        latex=r"\text{ExcessRet}_{3yr} = \prod_{t=1}^{3}(1 + R_{i,t}) - \prod_{t=1}^{3}(1 + R_{m,t})",
        description="Cumulative company return minus market return over 3 years",
        inputs={
            "annual_returns": "List of annual company returns",
            "market_returns": "List of annual S&P 500 returns",
        },
        output="Excess cumulative return",
        derivation_steps=[
            "1. Compound company annual returns: (1+r1)*(1+r2)*(1+r3) - 1",
            "2. Compound market annual returns: (1+m1)*(1+m2)*(1+m3) - 1",
            "3. Subtract: company_cumulative - market_cumulative",
        ],
        paper_reference="Paper 3: Multi-Factor Integration",
        valid_range=(-1.0, 5.0),
        unit="ratio",
    ),
    
    # --------------------------------------------------------------------------
    # Paper 4: Risk-Adjusted Returns & Volatility
    # --------------------------------------------------------------------------
    
    "annualized_volatility": FormulaSpec(
        name="Annualized Volatility",
        latex=r"\sigma_{annual} = \sigma_{daily} \times \sqrt{252}",
        description="Standard deviation of daily returns annualized",
        inputs={
            "daily_returns": "Array of daily price returns",
            "trading_days": "Number of trading days (typically 252)",
        },
        output="Annualized volatility",
        derivation_steps=[
            "1. Calculate daily returns: (P_t / P_{t-1}) - 1",
            "2. Compute standard deviation of daily returns",
            "3. Annualize: std_dev * sqrt(252)",
        ],
        paper_reference="Paper 4: Fundamental Drivers of R&D Returns",
        valid_range=(0.05, 1.5),
        unit="ratio (e.g., 0.30 = 30%)",
        notes=[
            "Values below 5% or above 150% indicate data issues",
            "252 trading days is standard assumption",
        ]
    ),
    
    "sharpe_ratio": FormulaSpec(
        name="Sharpe Ratio",
        latex=r"\text{Sharpe} = \frac{R_p - R_f}{\sigma_p}",
        description="Risk-adjusted return measure",
        inputs={
            "portfolio_return": "Portfolio average annual return",
            "risk_free_rate": "Risk-free rate (typically 10Y Treasury)",
            "portfolio_volatility": "Portfolio return standard deviation",
        },
        output="Sharpe ratio",
        derivation_steps=[
            "1. Calculate excess return: portfolio_return - risk_free_rate",
            "2. Calculate volatility of portfolio returns",
            "3. Divide: excess_return / volatility",
        ],
        paper_reference="Sharpe (1966)",
        valid_range=(-2.0, 4.0),
        unit="ratio",
        notes=[
            "Values > 1.0 considered good",
            "Values > 2.0 considered excellent",
            "Negative values indicate underperformance vs risk-free",
        ]
    ),
    
    # --------------------------------------------------------------------------
    # R&D Alpha Score (Composite)
    # --------------------------------------------------------------------------
    
    "rd_alpha_score": FormulaSpec(
        name="R&D Alpha Score",
        latex=r"\text{Alpha} = \frac{\text{RD\_Intensity} \times \text{Sector\_Adj} \times \text{Momentum} \times \text{Quality}}{\text{Volatility}}",
        description="Composite score integrating all research factors for ETF selection",
        inputs={
            "rd_intensity": "Capped R&D intensity (%)",
            "sector_adjustment": "Sector weight adjustment factor",
            "momentum_factor": "3-year momentum score",
            "quality_score": "Data quality score [0-1]",
            "volatility": "Annualized volatility",
        },
        output="Final ranking score for ETF inclusion",
        derivation_steps=[
            "1. Start with capped R&D intensity as base",
            "2. Multiply by sector adjustment (prevents overconcentration)",
            "3. Multiply by momentum factor (trend confirmation)",
            "4. Multiply by quality score (data reliability)",
            "5. Divide by volatility (risk normalization)",
            "6. Rank companies by final score",
        ],
        paper_reference="Composite: Papers 1-4",
        valid_range=(0.0, 100.0),
        unit="score",
        notes=[
            "Higher score = higher priority for ETF inclusion",
            "Score is relative, not absolute",
            "Top 20 scores typically selected for ETF",
        ]
    ),
    
    # --------------------------------------------------------------------------
    # Statistical Tests
    # --------------------------------------------------------------------------
    
    "anova_f_statistic": FormulaSpec(
        name="ANOVA F-Statistic",
        latex=r"F = \frac{MS_{between}}{MS_{within}} = \frac{SS_B / (k-1)}{SS_W / (N-k)}",
        description="Test statistic for comparing means across quintile portfolios",
        inputs={
            "ss_between": "Sum of squares between groups",
            "ss_within": "Sum of squares within groups",
            "k": "Number of groups (5 for quintiles)",
            "n": "Total number of observations",
        },
        output="F-statistic for hypothesis testing",
        derivation_steps=[
            "1. Group observations by quintile",
            "2. Calculate group means and grand mean",
            "3. Compute SS_between: sum of n_i * (mean_i - grand_mean)^2",
            "4. Compute SS_within: sum of (x_ij - mean_i)^2",
            "5. Calculate mean squares: MS = SS / df",
            "6. F = MS_between / MS_within",
        ],
        paper_reference="Standard ANOVA methodology",
        valid_range=(0.0, 100.0),
        unit="F-ratio",
    ),
    
    "eta_squared": FormulaSpec(
        name="Eta-Squared Effect Size",
        latex=r"\eta^2 = \frac{SS_{between}}{SS_{total}}",
        description="Proportion of variance explained by group membership",
        inputs={
            "ss_between": "Sum of squares between groups",
            "ss_total": "Total sum of squares",
        },
        output="Effect size [0, 1]",
        derivation_steps=[
            "1. Calculate SS_total = SS_between + SS_within",
            "2. Compute ratio: SS_between / SS_total",
        ],
        paper_reference="Cohen (1988)",
        valid_range=(0.0, 1.0),
        unit="ratio",
        notes=[
            "0.01 = small effect",
            "0.06 = medium effect",
            "0.14 = large effect",
        ]
    ),
    
    "cohens_d": FormulaSpec(
        name="Cohen's d Effect Size",
        latex=r"d = \frac{\bar{X}_1 - \bar{X}_2}{s_{pooled}}",
        description="Standardized mean difference between two groups",
        inputs={
            "mean1": "Mean of group 1 (e.g., Q5 high R&D)",
            "mean2": "Mean of group 2 (e.g., Q1 low R&D)",
            "std1": "Standard deviation of group 1",
            "std2": "Standard deviation of group 2",
            "n1": "Sample size of group 1",
            "n2": "Sample size of group 2",
        },
        output="Effect size in standard deviations",
        derivation_steps=[
            "1. Calculate pooled std: sqrt(((n1-1)*s1^2 + (n2-1)*s2^2) / (n1+n2-2))",
            "2. Compute d: (mean1 - mean2) / pooled_std",
        ],
        paper_reference="Cohen (1988)",
        valid_range=(-3.0, 3.0),
        unit="std devs",
        notes=[
            "0.2 = small effect",
            "0.5 = medium effect",
            "0.8 = large effect",
        ]
    ),
    
    "hac_standard_error": FormulaSpec(
        name="HAC Standard Error (Newey-West)",
        latex=r"SE_{HAC} = \sqrt{\frac{1}{T^2} \sum_{j=-L}^{L} K(j/L) \sum_t \hat{u}_t \hat{u}_{t-j}}",
        description="Heteroskedasticity and Autocorrelation Consistent standard errors",
        inputs={
            "residuals": "Regression residuals",
            "lags": "Number of lags (typically window_years - 1 for overlapping)",
            "kernel": "Kernel function (Bartlett default)",
        },
        output="Adjusted standard error",
        derivation_steps=[
            "1. Estimate initial regression to get residuals",
            "2. Choose lag length: L = window_years - 1 for overlapping windows",
            "3. Apply Bartlett kernel: K(x) = 1 - |x| for |x| <= 1",
            "4. Compute autocovariance terms",
            "5. Sum weighted autocovariances",
            "6. Take square root for standard error",
        ],
        paper_reference="Newey & West (1987)",
        valid_range=(0.0, None),
        unit="same as variable",
        notes=[
            "Essential for overlapping window analysis",
            "Corrects for autocorrelation in t-statistics",
            "Without HAC, p-values are biased downward",
        ]
    ),
    
    # --------------------------------------------------------------------------
    # Return Calculations
    # --------------------------------------------------------------------------
    
    "july_june_return": FormulaSpec(
        name="July-June Annual Return",
        latex=r"R_{T} = \frac{P_{June,T+1}}{P_{July,T}} - 1",
        description="Annual return following Fama-French convention to avoid look-ahead bias",
        inputs={
            "price_july_t": "Price at start of July in year T",
            "price_june_t1": "Price at end of June in year T+1",
        },
        output="Annual return",
        derivation_steps=[
            "1. Get closing price on July 1 of formation year T",
            "2. Get closing price on June 30 of year T+1",
            "3. Calculate return: (June_price / July_price) - 1",
        ],
        paper_reference="Fama & French (1993)",
        valid_range=(-0.9, 5.0),
        unit="ratio",
        notes=[
            "Ensures fiscal year data is public before using",
            "Accounts for typical 10-K filing delays",
            "Standard in academic factor research",
        ]
    ),
    
    "portfolio_cumulative_return": FormulaSpec(
        name="Cumulative Portfolio Return",
        latex=r"R_{cum} = \prod_{t=1}^{T}(1 + R_t) - 1",
        description="Total return from compounding annual returns",
        inputs={
            "annual_returns": "List of annual portfolio returns",
        },
        output="Total cumulative return",
        derivation_steps=[
            "1. Add 1 to each annual return",
            "2. Multiply all terms together",
            "3. Subtract 1 for total return",
        ],
        paper_reference="Standard portfolio methodology",
        valid_range=(-1.0, 100.0),
        unit="ratio",
    ),
}
