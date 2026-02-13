/**
 * PATH: frontend/src/components/InfoTooltipData.ts
 * PURPOSE: Centralized dictionary of metric explanations for InfoTooltip
 * WHY: Extracted from InfoTooltip.tsx to stay under 300-line limit. Pure data.
 */

export const METRIC_EXPLANATIONS: Record<string, { title: string; explanation: string; formula?: string }> = {
  annual_trading_cost: {
    title: "Annual Trading Cost",
    explanation:
      "The estimated return lost per year from trading frictions (bid-ask spread, market impact, commissions). Calculated as: round-trip cost × annual turnover. Uses Novy-Marx & Velikov (2016) methodology calibrated for S&P 500 liquidity.",
    formula: "Annual Cost = 2 × (Bid-Ask + Market Impact + Commission) × Turnover",
  },
  net_premium_after_costs: {
    title: "Net Premium After Costs (vs SPY)",
    explanation:
      "The RD20 strategy CAGR spread vs SPY CAGR (S&P 500 total-return proxy via split-adjusted close + dividends) after subtracting strategy trading costs. The backtest period is the period shown in the current publication snapshot, matching the characteristic premium sample and including major stress regimes. This is NOT the HML_RD factor. It is a benchmark-relative, implementable excess return available to a real investor.",
    formula: "Net Premium (pp/yr) = Strategy CAGR (net of costs) − SPY CAGR",
  },
  premium_capture_rate: {
    title: "Premium Capture Rate",
    explanation:
      "The percentage of the gross R&D premium that survives after trading costs. A rate near 100% means costs are small relative to the premium; a low rate means costs consume much of the premium.",
    formula: "Capture Rate = Net Premium ÷ Gross Premium × 100%",
  },
  gross_rd_premium: {
    title: "Gross R&D Premium",
    explanation:
      "The raw return difference between high-R&D stocks (Q5) and low-R&D stocks (Q1), before accounting for trading costs. This is the 'headline' premium from the academic literature.",
  },
  t_statistic: {
    title: "t-Statistic",
    explanation:
      "Measures how many standard errors the mean difference is from zero. Values above ~2 typically indicate statistical significance (p < 0.05). Higher absolute values = stronger evidence against the null hypothesis of no effect.",
    formula: "t = Mean Difference ÷ Standard Error",
  },
  p_value: {
    title: "p-Value",
    explanation:
      "The probability of observing results at least as extreme as ours if there were truly no effect. p < 0.05 is conventional significance; p < 0.01 is highly significant. Does NOT measure effect size.",
  },
  eta_squared: {
    title: "η² (Eta-Squared)",
    explanation:
      "Effect size from ANOVA: the proportion of total variance explained by R&D quintile membership. 0.01 = small, 0.06 = medium, 0.14 = large effect. Shows practical significance beyond statistical significance.",
    formula: "η² = SS_between ÷ SS_total",
  },
  cohens_d: {
    title: "Cohen's d",
    explanation:
      "Standardized effect size for t-tests: the mean difference expressed in standard deviation units. 0.2 = small, 0.5 = medium, 0.8 = large. Useful for comparing effects across studies.",
    formula: "d = (Mean₁ - Mean₂) ÷ Pooled SD",
  },
  sharpe_ratio: {
    title: "Sharpe Ratio",
    explanation:
      "Risk-adjusted return: excess return per unit of volatility. Higher is better. A Sharpe of 0.5 is decent; 1.0+ is strong. Assumes normally distributed returns.",
    formula: "Sharpe = (Return - Risk-Free Rate) ÷ Volatility",
  },
  max_drawdown: {
    title: "Maximum Drawdown",
    explanation:
      "The largest peak-to-trough decline in portfolio value. Shows worst-case loss if you bought at the top and sold at the bottom. Important for risk assessment.",
  },
  rd_intensity: {
    title: "R&D Intensity",
    explanation:
      "R&D expense divided by revenue, expressed as a percentage. Measures how much a firm invests in research relative to its size. Higher intensity = more R&D-focused business model.",
    formula: "R&D Intensity = (R&D Expense ÷ Revenue) × 100%",
  },
  hml_premium: {
    title: "HML_RD Premium (High-Minus-Low R&D)",
    explanation:
      "The within-universe return spread between the highest R&D quintile (Q5) and lowest R&D quintile (Q1) portfolios. Computed over non-overlapping July-June periods in the publication snapshot sample. A positive HML_RD means high-R&D firms outperformed low-R&D firms within the same universe for the same period. This is a characteristic premium, not a benchmark-relative strategy return.",
    formula: "HML_RD = Q5 Return − Q1 Return (within-universe)",
  },
  quintile: {
    title: "Quintile",
    explanation:
      "Each year, stocks are sorted by R&D intensity and divided into 5 equal-count groups. Q1 = lowest 20% R&D intensity, Q5 = highest 20%. Equal-weighted within each quintile.",
  },
  july_june_convention: {
    title: "July-June Return Convention",
    explanation:
      "Fama-French standard: fiscal-year accounting data is mapped to returns from July of the following year through June. This 6-month lag ensures all firms have filed their 10-Ks before portfolio formation, reducing look-ahead bias.",
  },
  delisting_adjustment: {
    title: "Exit / Delisting Treatment",
    explanation:
      'We do not inject a separate one-off "delisting return" into an annual return series. If a firm\'s price history ends before a return window ends (e.g., merger/delisting), we compute the holding-period return to the last observed trading day and treat cash as earning 0% thereafter for the remainder of the window. We also report delisting sensitivity as a robustness check.',
  },
  survivorship_bias: {
    title: "Survivorship Bias",
    explanation:
      "The tendency to overstate performance by only studying firms that survived. Dead firms often had poor returns. We mitigate this using point-in-time S&P 500 membership (when spans are available) and explicit exit handling plus sensitivity analysis. Tier-1 still has coverage limitations versus CRSP/Compustat-grade datasets.",
  },
  look_ahead_bias: {
    title: "Look-Ahead Bias",
    explanation:
      "Using information that wasn't available at the time of the investment decision. The July-June convention ensures we only use accounting data after it was publicly filed.",
  },
  alpha: {
    title: "Alpha (Regression Intercept)",
    explanation:
      "The return component not explained by factor exposures. A significant positive alpha means the R&D premium isn't fully captured by known factors (size, value, momentum, etc.).",
  },
  r_squared: {
    title: "R² (R-Squared)",
    explanation:
      "The proportion of return variance explained by the factor model. Higher R² = factors explain more of the return pattern. Low R² with significant alpha suggests a distinct premium.",
  },
  spanned: {
    title: "Spanned / Not Spanned",
    explanation:
      "'Spanned' means the factor model fully explains the premium (alpha ≈ 0). 'Not spanned' means a significant alpha remains after controlling for factors, suggesting the R&D premium is distinct.",
  },
  annual_turnover: {
    title: "Annual Turnover",
    explanation:
      "The fraction of portfolio holdings replaced each year. 40% turnover means 40% of positions are sold and replaced. Higher turnover = more trading costs.",
  },
  turnover: {
    title: "Turnover",
    explanation:
      "A measure of how much the portfolio changes at each rebalance. Higher turnover implies more trading and higher implementation costs. We report turnover using the standard weight-based definition (0.5 × sum of absolute weight changes).",
    formula: "Turnover = 0.5 × Σ |w_t - w_(t-1)|",
  },
  delisting_sensitivity: {
    title: "Delisting Sensitivity",
    explanation:
      "A robustness check that recomputes the annual HML premium under alternative assumptions for delisting returns. This tests whether the headline premium depends on uncertain delisting-return estimates.",
  },
  horizon_dependence: {
    title: "Horizon Dependence (Why 20-Year Can Be Lower)",
    explanation:
      "Long-horizon rolling windows are formed once and held for many years, so the R&D signal can become stale. Long horizons also mix multiple market regimes and selection effects (index turnover and delistings). Shorter horizons typically reflect fresher signal exposure.",
  },
  bid_ask_spread: {
    title: "Bid-Ask Spread",
    explanation:
      "The difference between the price to buy (ask) and sell (bid) a stock. For S&P 500 stocks, typically 5-10 basis points. This is a direct cost paid on each trade.",
  },
  market_impact: {
    title: "Market Impact",
    explanation:
      "The price movement caused by your own trade. Larger trades move prices more. For diversified portfolios with many small positions, impact is reduced.",
  },
  mispricing: {
    title: "Mispricing Hypothesis",
    explanation:
      "The premium exists because investors undervalue R&D (expensed, not capitalized), leading to systematic underpricing of innovative firms. Predicts premium in 'hard to arbitrage' stocks.",
  },
  risk_compensation: {
    title: "Risk Compensation Hypothesis",
    explanation:
      "The premium compensates for innovation risk: R&D outcomes are uncertain, and high-R&D firms have more volatile cash flows. Predicts premium in all segments.",
  },
  newey_west: {
    title: "Newey-West Standard Errors",
    explanation:
      "A statistical correction that accounts for autocorrelation and heteroskedasticity in time-series data. Because returns can be correlated across time, standard errors without this adjustment may be too small, leading to overstated significance. For the annual series we report a baseline lag=1 estimate and include a reviewer-friendly robustness panel for lags 0-3.",
    formula: "HAC-adjusted SE = √(Var + 2×Cov_lag1)",
  },
  rolling_window: {
    title: "Rolling Window Analysis",
    explanation:
      "A method where we compute statistics over a fixed-length window that 'rolls' through time. For example, a 5-year rolling window starting in 2000 covers 2000-2004, then 2001-2005, etc. Important: quintile assignments are made ONCE at window start and held for the entire period.",
  },
  non_overlapping: {
    title: "Non-Overlapping Returns",
    explanation:
      "Non-overlapping windows reduce mechanical overlap between observations (unlike rolling windows). This improves inference quality, but time-series dependence can still exist (regimes, volatility clustering), so we still use Newey-West standard errors on the annual series.",
  },
  overlapping_windows: {
    title: "Overlapping Windows (Descriptive Only)",
    explanation:
      "Windows that share time periods (e.g., 2000-2004 and 2001-2005 share 4 years). These are autocorrelated by construction and should NOT be used for p-values. We use them only for visualizing trends and regime dependence.",
  },
  gaap_expensing: {
    title: "GAAP R&D Expensing Rule",
    explanation:
      "Under U.S. GAAP (ASC 730, formerly SFAS 2), R&D costs must be expensed immediately rather than capitalized as an asset. This means R&D-intensive firms appear less profitable on paper even when building valuable intangible assets. This accounting treatment is central to the R&D premium hypothesis.",
  },
  point_in_time: {
    title: "Point-in-Time Universe",
    explanation:
      "Using only stocks that were actually in the index at each historical date, not stocks that are in the index today. This prevents survivorship bias because we include companies that later failed or were acquired.",
  },
  fiscal_year_lag: {
    title: "Fiscal Year Lag (6+ months)",
    explanation:
      "Companies have up to 90 days after fiscal year end to file 10-K reports. The July-June convention ensures a minimum 6-month lag between fiscal year end (typically December) and portfolio formation (July), so all accounting data is publicly available when we trade.",
  },
  equal_weight: {
    title: "Equal-Weight Portfolio",
    explanation:
      "Each stock in the portfolio receives the same dollar allocation. This contrasts with market-cap weighting where larger companies dominate. Equal-weighting gives more influence to smaller stocks and requires rebalancing to maintain equal weights.",
  },
  characteristic_premium: {
    title: "Characteristic Premium (vs Factor)",
    explanation:
      "A return pattern associated with a stock characteristic (like R&D intensity) without claiming it's a priced risk factor. We document an association, not causation. The premium could reflect mispricing, risk, or both.",
  },
  win_rate: {
    title: "Win Rate",
    explanation:
      "The percentage of periods where the strategy was profitable. A 70% win rate means the high-R&D portfolio beat low-R&D in 70% of years. High win rates suggest consistent, not just average, outperformance.",
  },
  regime_dependence: {
    title: "Regime Dependence",
    explanation:
      "The premium varies across market conditions (bull/bear markets, high/low volatility periods). Understanding regime dependence helps set realistic expectations: the strategy won't work every year.",
  },
  signal_staleness: {
    title: "Signal Staleness",
    explanation:
      "Over time, the predictive power of a signal decays. A company's R&D intensity from 2000 tells you little about its innovation in 2020. This is why annual rebalancing captures more premium than buy-and-hold.",
  },
  competitive_diffusion: {
    title: "Competitive Diffusion",
    explanation:
      "R&D advantages erode over time through imitation, patent expiration, and knowledge spillovers. Today's innovation leader may be tomorrow's laggard. This contributes to signal staleness in long horizons.",
  },
  sector_tilt: {
    title: "Sector Tilt",
    explanation:
      "High-R&D portfolios naturally overweight Technology and Healthcare because these sectors invest more in R&D. Some of the premium may reflect sector exposure rather than pure R&D effects. We report sector composition for transparency.",
  },
  double_sort: {
    title: "Double-Sort Analysis",
    explanation:
      "First sort stocks by one variable (e.g., size), then within each group, sort by another (e.g., R&D). This tests whether the R&D premium exists after controlling for the first variable. If the premium persists within size groups, it's not just a size effect.",
  },
  tercile: {
    title: "Tercile",
    explanation:
      "Dividing stocks into 3 equal groups. Terciles are used when sample sizes are smaller (like within-size groups) because quintiles would have too few stocks per bucket.",
  },
  rebalancing_calendar: {
    title: "Annual Rebalancing Calendar",
    explanation:
      "The strategy rebalances once per year in late June/early July. This timing ensures: (1) all 10-K filings are in (90-day deadline from Dec fiscal year end), (2) alignment with academic July-June convention, (3) minimal trading to capture the R&D premium.",
  },
  formation_date: {
    title: "Formation Date",
    explanation:
      "The date when portfolio holdings are determined. For R&D Alpha, this is end of June each year. You rank all S&P 500 stocks by prior-year R&D/Revenue, select the top N, and hold for 12 months.",
  },
  holding_period: {
    title: "Holding Period",
    explanation:
      "The time between rebalances (July 1 through June 30). Annual rebalancing captures the R&D premium while keeping turnover and costs low. More frequent rebalancing doesn't improve returns but increases costs.",
  },
  execution_slippage: {
    title: "Execution Slippage",
    explanation:
      "The difference between the expected price and actual execution price. For liquid S&P 500 stocks traded over several days, slippage is typically 5-15 bps. Avoid trading all positions on the same day.",
  },
  capacity_constraint: {
    title: "Capacity Constraint",
    explanation:
      "The maximum AUM before market impact erodes returns. For a 20-stock S&P 500 strategy, capacity is likely $500M-$2B depending on execution quality. Larger funds should use more holdings or gradual execution.",
  },
  tracking_error: {
    title: "Tracking Error",
    explanation:
      "Standard deviation of excess returns vs benchmark. Higher tracking error means more deviation from the market. R&D Alpha has ~8-12% annual tracking error vs S&P 500, which feels uncomfortable but is where the alpha comes from.",
  },
  tax_efficiency: {
    title: "Tax Efficiency",
    explanation:
      "Low turnover (~15% avg) means most gains are long-term. Annual rebalancing qualifies positions for long-term capital gains rates. Consider tax-loss harvesting in down years.",
  },
  broker_selection: {
    title: "Broker Selection",
    explanation:
      "Choose a broker with low commission and good execution quality. For 20 S&P 500 stocks, most retail brokers (Schwab, Fidelity, Interactive Brokers) work well. Avoid payment-for-order-flow brokers for larger accounts.",
  },
  data_sources: {
    title: "Data Sources for DIY",
    explanation:
      "R&D expense and revenue ultimately come from 10-K filings (SEC EDGAR). This platform uses a Tier-1 vendor feed (FMP) to standardize fundamentals and daily prices; total returns are constructed from split-adjusted closes plus dividend events (reinvested). Universe eligibility uses addition-date gating from a curated constituent dataset (Tier-1) with documented limitations; see the Universe Integrity table in the paper. The frozen snapshot is shipped for exact replication even without redistributing raw vendor data.",
  },
  position_sizing: {
    title: "Position Sizing",
    explanation:
      "Equal-weight means each position is 5% of the portfolio (for 20 stocks). At rebalance, sell overweight positions and buy underweight ones. Small deviations (±1%) don't require immediate action.",
  },
  rebalance_tolerance: {
    title: "Rebalance Tolerance",
    explanation:
      "How far a position can drift before correcting. A 5% target with ±2% tolerance (3-7%) reduces unnecessary trading. Only rebalance if drift exceeds tolerance or at the annual June date.",
  },
}
