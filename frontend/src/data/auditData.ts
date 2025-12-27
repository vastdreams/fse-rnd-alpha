/**
 * PATH: frontend/src/data/auditData.ts
 * PURPOSE: Pre-computed audit explanations for ETF metrics
 * 
 * These explanations are generated once and stored to avoid
 * repeated API calls for the same data audit information.
 * 
 * Each metric has a chain-of-thought breakdown showing:
 * - Data sources (APIs, tables, calculations)
 * - Computation steps
 * - Formulas used
 * - AI analysis of the metric's meaning
 */

import type { AuditData } from "@/components/AuditModal"

export const auditDataMap: Record<string, (params: Record<string, unknown>) => AuditData> = {
  
  // Annualized Return
  annualized_return: (params) => ({
    metricId: "annualized_return",
    metricName: "Annualized Return",
    value: `+${params.value || "27.1"}%`,
    period: `${params.startYear || 2005}-${params.endYear || 2023} (${(params.endYear as number || 2023) - (params.startYear as number || 2005)} years)`,
    status: "warning",
    statusText: "Survivorship bias present",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Data Source Identification",
        description: "Fetching annual returns for portfolio holdings from July-June return series",
        sources: [
          { label: "API Endpoint", value: "/api/portfolio/backtest" },
          { label: "Return Convention", value: "July-June (Fama-French)" },
          { label: "Period", value: `${params.startYear || 2005}-${params.endYear || 2023}` },
          { label: "Holdings", value: `Top ${params.nHoldings || 20} R&D companies` },
        ],
      },
      {
        stepNumber: 2,
        type: "source",
        title: "Annual Portfolio Returns",
        description: "For each July, select ETF holdings using point-in-time FY(T-1) data and calculate equal-weighted return",
        sources: [
          { label: "Selection Method", value: "R&D Alpha scoring (point-in-time)" },
          { label: "Formation Date", value: "July 1 (Fama-French convention)" },
          { label: "Data Used", value: "FY(T-1) financials" },
          { label: "Weighting", value: "Equal weight at formation" },
          { label: "Return Source", value: "july_june_returns table" },
        ],
        note: "Portfolio uses eligibility gates to prevent survivorship bias (listing, filing, liquidity)"
      },
      {
        stepNumber: 3,
        type: "computation",
        title: "Compound Annual Returns",
        description: "Calculate total return by compounding each year's return",
        formula: `Total Return = ∏(1 + Rᵢ) - 1\nwhere Rᵢ = annual return for year i`,
        sources: [
          { label: "Years", value: `${(params.endYear as number || 2023) - (params.startYear as number || 2005)} annual periods` },
        ],
      },
      {
        stepNumber: 4,
        type: "formula",
        title: "Annualization Formula",
        description: "Convert total return to annualized return using geometric mean",
        formula: `Annualized Return = (1 + Total Return)^(1/n) - 1\n\nwhere n = number of years\n\nExample: (1 + 94.92)^(1/18) - 1 = 27.1%`,
      },
      {
        stepNumber: 5,
        type: "info",
        title: "Important Caveats",
        description: "This return is inflated due to survivorship bias",
        note: "The backtest includes companies like HOOD, COIN, MRNA that were not in the S&P 500 during historical periods but had extraordinary post-IPO returns. Realistic R&D premium is +5-8% over market."
      }
    ],
    aiAnalysis: `**Metric Analysis: Annualized Return**

The reported +${params.value || "27.1"}% annualized return represents the geometric mean of annual portfolio returns over the backtest period.

**Key Observations:**
1. **Methodology**: The portfolio uses a Fama-French July-June return convention, selecting top R&D companies based on prior fiscal year filings.

2. **Survivorship Bias Warning**: This figure is INFLATED because:
   - Companies like Robinhood (HOOD), Coinbase (COIN), and Moderna (MRNA) are included in historical portfolios
   - These companies weren't public/in the S&P 500 during those periods
   - Their extraordinary post-IPO returns artificially boost historical performance

3. **Realistic Expectation**: Academic research suggests the R&D premium is typically +5-8% annually over the market, not +17%. The high reported excess return should be interpreted as an upper bound.

4. **Recommendation**: Use this as a directional indicator of R&D's alpha potential, but expect actual returns to be lower when implementing.`
  }),

  // S&P 500 Benchmark Return
  sp500_return: (params) => ({
    metricId: "sp500_return",
    metricName: "S&P 500 (Annualized)",
    value: `+${params.value || "9.8"}%`,
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "verified",
    statusText: "Fama-French data",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Data Source Identification",
        description: "Fetching S&P 500 market returns from Fama-French factor database",
        sources: [
          { label: "Data Source", value: "Fama-French Factors" },
          { label: "Table", value: "fama_french_factors" },
          { label: "Frequency", value: "Annual" },
        ],
      },
      {
        stepNumber: 2,
        type: "computation",
        title: "Market Return Calculation",
        description: "S&P 500 return is computed as MKT-RF + RF (market excess return plus risk-free rate)",
        formula: `Market Return = MKT-RF + RF\n\nwhere:\n  MKT-RF = Market excess return over risk-free rate\n  RF = Risk-free rate (typically 3-month T-bill)`,
        sources: [
          { label: "MKT-RF", value: "Market excess return" },
          { label: "RF", value: "Risk-free rate" },
        ],
      },
      {
        stepNumber: 3,
        type: "aggregation",
        title: "Annualization",
        description: "Compound annual returns and calculate geometric mean",
        formula: `Annualized Return = (1 + Total Return)^(1/n) - 1`,
      },
    ],
    aiAnalysis: `**Metric Analysis: S&P 500 Benchmark Return**

The +${params.value || "9.8"}% represents the annualized total return of the S&P 500 market index.

**Data Quality:**
- Sourced from the authoritative Fama-French factor database
- Calculated as MKT-RF + RF to get total market return
- Aligned with July-June convention for consistency with portfolio returns

**Historical Context:**
- This period (${params.startYear || 2005}-${params.endYear || 2023}) includes:
  - 2008 Financial Crisis
  - Post-crisis bull market (2009-2020)
  - COVID crash and recovery (2020)
  - 2022 bear market
- Long-term S&P 500 average is ~10% annually, so this is in line with historical norms.`
  }),

  // Excess Return
  excess_return: (params) => ({
    metricId: "excess_return",
    metricName: "Excess Return (Annual)",
    value: `+${params.value || "17.4"}%`,
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "warning",
    statusText: "Contains survivorship bias",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Component Identification",
        description: "Identifying the two components needed for excess return calculation",
        sources: [
          { label: "Portfolio Return", value: `+${params.portfolioReturn || "27.1"}% annualized` },
          { label: "Benchmark Return", value: `+${params.benchmarkReturn || "9.8"}% annualized` },
        ],
      },
      {
        stepNumber: 2,
        type: "formula",
        title: "Excess Return Calculation",
        description: "Simple difference between portfolio and benchmark returns",
        formula: `Excess Return = Portfolio Return - Benchmark Return\n\n= ${params.portfolioReturn || "27.1"}% - ${params.benchmarkReturn || "9.8"}%\n= ${params.value || "17.4"}%`,
      },
      {
        stepNumber: 3,
        type: "info",
        title: "Interpretation",
        description: "This represents the 'R&D premium' - the additional return from investing in high R&D companies",
        note: "Academic research suggests realistic R&D premium is +5-8% annually. The higher figure here is due to survivorship bias in the backtest."
      },
    ],
    aiAnalysis: `**Metric Analysis: Excess Return (R&D Premium)**

The +${params.value || "17.4"}% excess return represents how much the R&D-focused portfolio outperformed the S&P 500 on an annualized basis.

**Critical Warning:**
This figure is OVERSTATED due to survivorship bias. The backtest includes:
- Future IPOs (HOOD 2021, COIN 2021) in historical portfolios
- Companies with extraordinary post-IPO performance
- Stocks that weren't actually available for investment at the time

**Academic Perspective:**
Research on the R&D-returns relationship typically finds:
- Lev & Sougiannis (1996): R&D has predictive power for returns
- Chan et al. (2001): R&D intensity predicts cross-sectional returns
- Typical premium: 5-8% annually

**Recommendation:**
Expect actual excess returns of 5-8% over the market when implementing this strategy with proper survivorship-bias-free data.`
  }),

  // Total Value ($100 becomes)
  total_value: (params) => ({
    metricId: "total_value",
    metricName: "$100 Becomes",
    value: `$${params.value || "9,592"}`,
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "info",
    statusText: "Hypothetical growth",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Starting Value",
        description: "Hypothetical initial investment",
        sources: [
          { label: "Initial Investment", value: "$100" },
          { label: "Start Date", value: `July ${params.startYear || 2005}` },
        ],
      },
      {
        stepNumber: 2,
        type: "computation",
        title: "Apply Total Return",
        description: "Multiply initial investment by (1 + total return)",
        formula: `Final Value = Initial × (1 + Total Return)\n\n= $100 × (1 + ${params.totalReturn || "94.92"})\n= $${params.value || "9,592"}`,
        sources: [
          { label: "Total Return", value: `${params.totalReturn || "9492"}%` },
        ],
      },
      {
        stepNumber: 3,
        type: "info",
        title: "Comparison to S&P 500",
        description: "Same $100 invested in S&P 500",
        sources: [
          { label: "S&P 500 Final Value", value: `$${params.sp500Value || "589"}` },
          { label: "Outperformance", value: `${((parseFloat(String(params.value || "9592").replace(",", "")) / parseFloat(String(params.sp500Value || "589"))) * 100 - 100).toFixed(0)}%` },
        ],
      },
    ],
    aiAnalysis: `**Metric Analysis: Portfolio Growth**

This shows the hypothetical growth of $100 invested in the R&D Alpha portfolio.

**Calculation:**
- Start: $100 in July ${params.startYear || 2005}
- End: $${params.value || "9,592"} in June ${params.endYear || 2023}
- Total Return: ${params.totalReturn || "9,492"}%

**Comparison:**
- S&P 500: $100 → $${params.sp500Value || "589"}
- R&D Portfolio outperformed by ~${((parseFloat(String(params.value || "9592").replace(",", "")) / parseFloat(String(params.sp500Value || "589")))).toFixed(0)}x

**Important Notes:**
1. This is a HYPOTHETICAL backtest, not actual returns
2. Does not account for trading costs, taxes, or slippage
3. Subject to survivorship bias (see other metrics)
4. Past performance does not guarantee future results`
  }),

  // Sharpe Ratio
  sharpe_ratio: (params) => ({
    metricId: "sharpe_ratio",
    metricName: "Sharpe Ratio",
    value: String(params.value || "0.96"),
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "verified",
    statusText: "Risk-adjusted return",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Data Components",
        description: "Gathering components needed for Sharpe ratio calculation",
        sources: [
          { label: "Annual Returns", value: "18 annual return observations" },
          { label: "Risk-Free Rate", value: "Fama-French RF factor" },
          { label: "Volatility", value: "Standard deviation of annual returns" },
        ],
      },
      {
        stepNumber: 2,
        type: "computation",
        title: "Calculate Excess Return",
        description: "Portfolio return minus average risk-free rate",
        formula: `Excess Return = Portfolio Return - Avg RF\n= ${params.portfolioReturn || "27.1"}% - ${params.avgRf || "2.0"}%\n= ${params.excessReturn || "25.1"}%`,
      },
      {
        stepNumber: 3,
        type: "formula",
        title: "Sharpe Ratio Formula",
        description: "Excess return divided by volatility",
        formula: `Sharpe Ratio = (Rp - Rf) / σp\n\nwhere:\n  Rp = Portfolio annualized return\n  Rf = Risk-free rate\n  σp = Portfolio volatility (std dev)\n\n= ${params.excessReturn || "25.1"}% / ${params.volatility || "26.2"}%\n= ${params.value || "0.96"}`,
      },
      {
        stepNumber: 4,
        type: "info",
        title: "Interpretation",
        description: "What the Sharpe ratio tells us",
        note: "A Sharpe ratio of ~1.0 means you're getting about 1 unit of return for each unit of risk. Generally: <1 = poor, 1-2 = good, >2 = excellent."
      },
    ],
    aiAnalysis: `**Metric Analysis: Sharpe Ratio**

The Sharpe ratio of ${params.value || "0.96"} measures risk-adjusted return.

**Interpretation:**
- For every 1% of volatility, the portfolio generates ~1% of excess return
- This is considered "good" (between 1-2 is typically strong)
- Indicates the high returns come with proportional risk

**Benchmarks:**
- S&P 500 long-term Sharpe: ~0.4-0.5
- Hedge funds average: ~0.5-0.7
- This portfolio: ${params.value || "0.96"} (above average)

**Caveats:**
- Sharpe ratio can be manipulated by smoothing returns
- Annual data has fewer observations than monthly
- Assumes normal distribution of returns`
  }),

  // Max Drawdown
  max_drawdown: (params) => ({
    metricId: "max_drawdown",
    metricName: "Max Drawdown",
    value: `${params.value || "-23.1"}%`,
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "info",
    statusText: "Peak-to-trough decline",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Cumulative Return Series",
        description: "Build cumulative return series from annual returns",
        sources: [
          { label: "Data Points", value: "18 annual returns" },
          { label: "Calculation", value: "Cumulative product of (1 + annual return)" },
        ],
      },
      {
        stepNumber: 2,
        type: "computation",
        title: "Running Maximum",
        description: "Calculate running maximum at each point",
        formula: `Running Max[t] = max(Cumulative[1], ..., Cumulative[t])`,
      },
      {
        stepNumber: 3,
        type: "formula",
        title: "Drawdown Calculation",
        description: "Calculate drawdown at each point as decline from running max",
        formula: `Drawdown[t] = Cumulative[t] / Running Max[t] - 1\n\nMax Drawdown = min(all Drawdowns)\n= ${params.value || "-23.1"}%`,
      },
      {
        stepNumber: 4,
        type: "info",
        title: "Context",
        description: "When did the max drawdown occur?",
        note: "The largest drawdown likely occurred during 2008-2009 (Financial Crisis) or 2022 (tech selloff). High R&D companies are typically growth stocks with higher volatility."
      },
    ],
    aiAnalysis: `**Metric Analysis: Maximum Drawdown**

The ${params.value || "-23.1"}% max drawdown represents the largest peak-to-trough decline in the portfolio.

**What This Means:**
- At some point, the portfolio lost ${Math.abs(parseFloat(String(params.value || "-23.1")))}% from its previous high
- This is the "worst case" scenario for an investor who bought at the peak

**Historical Context:**
- S&P 500 max drawdown 2008: ~-55%
- This portfolio's drawdown is lower, suggesting some resilience
- However, annual data may miss intra-year drawdowns

**Risk Consideration:**
- Investors should be prepared for ~25% declines
- High R&D companies are growth stocks with elevated volatility
- Dollar-cost averaging helps mitigate drawdown risk`
  }),

  // Volatility
  volatility: (params) => ({
    metricId: "volatility",
    metricName: "Volatility",
    value: `${params.value || "26.2"}%`,
    period: `${params.startYear || 2005}-${params.endYear || 2023}`,
    status: "info",
    statusText: "Annual standard deviation",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Annual Return Series",
        description: "Collect annual portfolio returns",
        sources: [
          { label: "Observations", value: "18 annual returns" },
          { label: "Time Period", value: `${params.startYear || 2005}-${params.endYear || 2023}` },
        ],
      },
      {
        stepNumber: 2,
        type: "formula",
        title: "Standard Deviation Formula",
        description: "Calculate volatility as standard deviation of annual returns",
        formula: `σ = √[Σ(Ri - R̄)² / (n-1)]\n\nwhere:\n  Ri = return in year i\n  R̄ = mean annual return\n  n = number of years`,
      },
    ],
    aiAnalysis: `**Metric Analysis: Portfolio Volatility**

The ${params.value || "26.2"}% volatility represents the standard deviation of annual returns.

**Context:**
- S&P 500 historical volatility: ~15-18%
- This portfolio: ${params.value || "26.2"}% (about 50% more volatile)
- Higher volatility is expected for growth/R&D-heavy portfolios

**Implications:**
- In a typical year, returns could range from +${(27.1 - 26.2).toFixed(0)}% to +${(27.1 + 26.2).toFixed(0)}%
- Two standard deviations covers ~95% of outcomes: -${(26.2 * 2 - 27.1).toFixed(0)}% to +${(27.1 + 26.2 * 2).toFixed(0)}%

**Trade-off:**
The higher returns come with higher volatility - this is the classic risk-return trade-off.`
  }),

  // R&D Intensity (for holdings)
  rd_intensity: (params) => ({
    metricId: "rd_intensity",
    metricName: "R&D Intensity",
    value: `${params.value || "15.2"}%`,
    period: `FY${params.year || 2023}`,
    status: "verified",
    statusText: "SEC filing data",
    lastUpdated: new Date().toISOString().split("T")[0],
    steps: [
      {
        stepNumber: 1,
        type: "source",
        title: "Financial Data Source",
        description: "R&D expense and revenue from company's 10-K filing",
        sources: [
          { label: "Data Provider", value: "Financial Modeling Prep (FMP)" },
          { label: "Filing Type", value: "10-K Annual Report" },
          { label: "Fiscal Year", value: `FY${params.year || 2023}` },
          { label: "Table", value: "fmp_income_statements" },
        ],
      },
      {
        stepNumber: 2,
        type: "formula",
        title: "R&D Intensity Calculation",
        description: "R&D expenses as a percentage of revenue",
        formula: `R&D Intensity = (R&D Expenses / Revenue) × 100\n\n= ($${params.rdExpense || "X"}M / $${params.revenue || "Y"}M) × 100\n= ${params.value || "15.2"}%`,
      },
      {
        stepNumber: 3,
        type: "info",
        title: "Sector Context",
        description: "How this compares to industry averages",
        note: "Technology and Healthcare companies typically have 10-25% R&D intensity. >15% is considered high."
      },
    ],
    aiAnalysis: `**Metric Analysis: R&D Intensity**

R&D Intensity of ${params.value || "15.2"}% indicates the company invests heavily in innovation.

**Calculation:**
R&D Intensity = R&D Expenses / Total Revenue

**Sector Benchmarks:**
- Tech average: 12-15%
- Pharma/Biotech: 15-25%
- Consumer goods: 2-5%
- This company: ${params.value || "15.2"}% (high)

**Investment Thesis:**
High R&D intensity is associated with:
- Future revenue growth potential
- Competitive moat through innovation
- Higher volatility but potentially higher returns

The R&D Alpha strategy specifically targets high R&D companies based on academic research showing this characteristic predicts outperformance.`
  }),
}

// Helper function to get audit data for a metric
export function getAuditData(
  metricId: string, 
  params: Record<string, unknown> = {}
): AuditData | null {
  const generator = auditDataMap[metricId]
  if (!generator) return null
  return generator(params)
}

