/**
 * PATH: frontend/src/components/InfoTooltip.tsx
 * PURPOSE:
 *   - Provide inline explanatory tooltips for technical metrics and concepts
 *   - Help readers understand what numbers mean in the research papers
 *
 * USAGE:
 *   <InfoTooltip term="premium_capture_rate" />
 *   <InfoTooltip term="t_statistic" inline />
 *   <InfoTooltip>Custom explanation text</InfoTooltip>
 */

import { HelpCircle, Info } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

// Centralized dictionary of metric explanations
export const METRIC_EXPLANATIONS: Record<string, { title: string; explanation: string; formula?: string }> = {
  // Transaction cost metrics
  annual_trading_cost: {
    title: "Annual Trading Cost",
    explanation:
      "The estimated return lost per year from trading frictions (bid-ask spread, market impact, commissions). Calculated as: round-trip cost × annual turnover. Uses Novy-Marx & Velikov (2016) methodology calibrated for S&P 500 liquidity.",
    formula: "Annual Cost = 2 × (Bid-Ask + Market Impact + Commission) × Turnover",
  },
  net_premium_after_costs: {
    title: "Net Premium After Costs",
    explanation:
      "The R&D premium (Q5 minus benchmark) after subtracting strategy trading costs and benchmark index fund costs. This shows the implementable alpha available to a real investor.",
    formula: "Net Premium = (Q5 Gross - Trading Cost) - (Benchmark Gross - Index Cost)",
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

  // Statistical metrics
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

  // R&D metrics
  rd_intensity: {
    title: "R&D Intensity",
    explanation:
      "R&D expense divided by revenue, expressed as a percentage. Measures how much a firm invests in research relative to its size. Higher intensity = more R&D-focused business model.",
    formula: "R&D Intensity = (R&D Expense ÷ Revenue) × 100%",
  },
  hml_premium: {
    title: "HML Premium (High-Minus-Low)",
    explanation:
      "The return spread between the highest quintile (Q5, high R&D) and lowest quintile (Q1, low R&D) portfolios. A positive HML means high-R&D firms outperformed.",
    formula: "HML = Q5 Return - Q1 Return",
  },
  quintile: {
    title: "Quintile",
    explanation:
      "Each year, stocks are sorted by R&D intensity and divided into 5 equal-count groups. Q1 = lowest 20% R&D intensity, Q5 = highest 20%. Equal-weighted within each quintile.",
  },

  // Methodology
  july_june_convention: {
    title: "July-June Return Convention",
    explanation:
      "Fama-French standard: fiscal-year accounting data is mapped to returns from July of the following year through June. This 6-month lag ensures all firms have filed their 10-Ks before portfolio formation, reducing look-ahead bias.",
  },
  delisting_adjustment: {
    title: "Delisting Adjustment",
    explanation:
      "When a stock delists (bankruptcy, merger, etc.), we include delisting returns to avoid survivorship bias. Without this, we'd only see survivors, overstating average returns.",
  },
  survivorship_bias: {
    title: "Survivorship Bias",
    explanation:
      "The tendency to overstate performance by only studying firms that survived. Dead firms often had poor returns. We mitigate this using historical S&P 500 membership and delisting returns.",
  },
  look_ahead_bias: {
    title: "Look-Ahead Bias",
    explanation:
      "Using information that wasn't available at the time of the investment decision. The July-June convention ensures we only use accounting data after it was publicly filed.",
  },

  // Factor spanning
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

  // Portfolio parameters
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

  // Interpretation
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
}

interface InfoTooltipProps {
  /** Predefined term from METRIC_EXPLANATIONS */
  term?: keyof typeof METRIC_EXPLANATIONS
  /** Custom explanation (overrides term) */
  children?: React.ReactNode
  /** Custom title for custom explanations */
  title?: string
  /** Show as inline text with icon vs standalone icon */
  inline?: boolean
  /** Use Info icon instead of HelpCircle */
  infoIcon?: boolean
  /** Additional className */
  className?: string
  /** Icon size */
  size?: number
}

export function InfoTooltip({
  term,
  children,
  title,
  inline = false,
  infoIcon = false,
  className,
  size = 14,
}: InfoTooltipProps) {
  const explanation = term ? METRIC_EXPLANATIONS[term] : null

  const tooltipTitle = title || explanation?.title
  const tooltipContent = children || explanation?.explanation
  const formula = explanation?.formula

  if (!tooltipContent) {
    console.warn(`InfoTooltip: No explanation found for term "${term}"`)
    return null
  }

  const Icon = infoIcon ? Info : HelpCircle

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={cn(
              "inline-flex items-center justify-center rounded-full",
              "text-muted-foreground hover:text-foreground transition-colors",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
              inline ? "ml-1" : "",
              className
            )}
            aria-label={`Learn more about ${tooltipTitle || "this metric"}`}
          >
            <Icon size={size} className="flex-shrink-0" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" className="max-w-sm">
          {tooltipTitle && (
            <p className="font-semibold text-popover-foreground mb-1">{tooltipTitle}</p>
          )}
          <p className="text-muted-foreground text-xs leading-relaxed">{tooltipContent}</p>
          {formula && (
            <p className="text-muted-foreground text-xs mt-2 font-mono bg-muted/60 border border-border/50 px-2 py-1 rounded">
              {formula}
            </p>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

/**
 * Convenience component for wrapping a metric value with its explanation
 */
interface MetricWithTooltipProps {
  term: keyof typeof METRIC_EXPLANATIONS
  value: React.ReactNode
  label?: string
  className?: string
}

export function MetricWithTooltip({ term, value, label, className }: MetricWithTooltipProps) {
  return (
    <div className={cn("flex items-center gap-1", className)}>
      {label && <span className="text-muted-foreground text-xs">{label}</span>}
      <span className="font-semibold">{value}</span>
      <InfoTooltip term={term} size={12} />
    </div>
  )
}

export default InfoTooltip

