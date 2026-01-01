/**
 * PATH: frontend/src/components/Formula.tsx
 * PURPOSE: Renders mathematical formulas with proper formatting (subscripts, superscripts, Greek letters)
 */

import { cn } from "@/lib/utils"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface FormulaProps {
  children: React.ReactNode
  className?: string
  block?: boolean
  compact?: boolean
  label?: string
  description?: string
}

/**
 * Formula component for displaying mathematical expressions
 * Uses proper HTML for subscripts/superscripts with mathematical styling
 */
export function Formula({ children, className, block = false, compact = false, label, description }: FormulaProps) {
  if (block) {
    return (
      <div className={cn(
        "my-2 border border-border/50 rounded-lg bg-muted/30",
        compact ? "px-3 py-2" : "px-4 py-3",
        className
      )}>
        {label && (
          description ? (
            <TooltipProvider delayDuration={0}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    type="button"
                    aria-label={`Learn more about ${label}`}
                    className={cn(
                      "group w-full text-left",
                      "font-medium text-muted-foreground uppercase tracking-wider",
                      "inline-flex items-center gap-2",
                      "cursor-help select-text",
                      "focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded-sm",
                      compact ? "text-[10px] mb-1" : "text-xs mb-2"
                    )}
                  >
                    <span className="underline decoration-dotted underline-offset-2">
                      {label}
                    </span>
                    <span
                      aria-hidden="true"
                      className={cn(
                        "inline-flex h-5 w-5 items-center justify-center rounded-full border",
                        "border-border/60 bg-background/70",
                        "text-[11px] font-semibold",
                        "text-blue-700 dark:text-blue-300",
                        "group-hover:bg-muted group-hover:text-blue-800 dark:group-hover:text-blue-200",
                        "transition-colors"
                      )}
                    >
                      ?
                    </span>
                  </button>
                </TooltipTrigger>
                <TooltipContent
                  side="top"
                  align="start"
                  className="max-w-sm text-sm font-normal normal-case tracking-normal z-50"
                >
                  <p>{description}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <div className={cn(
              "font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2",
              compact ? "text-[10px] mb-1" : "text-xs mb-2"
            )}>
              {label}
            </div>
          )
        )}
        <div className={cn(
          "font-serif italic text-emerald-500 dark:text-emerald-400",
          compact ? "text-base" : "text-lg"
        )}>
          {children}
        </div>
      </div>
    )
  }

  return (
    <span className={cn(
      "font-serif italic text-emerald-600 dark:text-emerald-400",
      className
    )}>
      {children}
    </span>
  )
}

// Sub-components for mathematical notation
export function Sub({ children }: { children: React.ReactNode }) {
  return <sub className="text-[0.65em] relative -bottom-[0.25em]">{children}</sub>
}

export function Sup({ children }: { children: React.ReactNode }) {
  return <sup className="text-[0.65em] relative -top-[0.5em]">{children}</sup>
}

export function Var({ children }: { children: React.ReactNode }) {
  return <span className="font-serif italic">{children}</span>
}

export function Greek({ children, className }: { children: React.ReactNode; className?: string }) {
  return <span className={cn("font-serif", className)}>{children}</span>
}

// Fraction helper component
function Frac({ num, den }: { num: React.ReactNode; den: React.ReactNode }) {
  return (
    <span className="inline-flex flex-col items-center mx-1 text-[0.85em]">
      <span>{num}</span>
      <span className="border-t border-current w-full my-px"></span>
      <span>{den}</span>
    </span>
  )
}

// Pre-defined common formulas with explanations
export const Formulas = {
  RDIntensity: () => (
    <Formula block compact label="R&D Intensity" description="Measures how much a firm invests in R&D relative to its size. Higher values indicate more R&D-intensive business models (e.g., biotech firms often exceed 20%, while utilities are near 0%).">
      <Var>R&D Intensity</Var> = <Frac num="R&D Expense" den="Revenue" /> × 100%
    </Formula>
  ),
  
  ANOVA: () => (
    <Formula block compact label="ANOVA Model" description="Analysis of Variance tests whether average returns differ significantly across R&D quintiles. μ is the grand mean return, αᵢ captures the effect of being in quintile i, and εᵢⱼ is the residual (unexplained variation).">
      <Var>Return</Var><Sub>ij</Sub> = <Greek>μ</Greek> + <Greek>α</Greek><Sub>i</Sub> + <Greek>ε</Greek><Sub>ij</Sub>
      <span className="text-xs text-muted-foreground ml-3 not-italic font-sans">
        (α<Sub>i</Sub> = quintile effect)
      </span>
    </Formula>
  ),
  
  EtaSquared: () => (
    <Formula block compact label="η² (Effect Size)" description="Proportion of total return variance explained by quintile membership. Values: 0.01 = small (1% explained), 0.06 = medium (6%), 0.14 = large (14%). Unlike p-values, η² tells you how much the grouping matters practically.">
      <Greek>η</Greek><Sup>2</Sup> = <Frac num={<>SS<Sub>between</Sub></>} den={<>SS<Sub>total</Sub></>} />
    </Formula>
  ),
  
  CohensD: () => (
    <Formula block compact label="Cohen's d" description="Standardized difference between Q5 and Q1 mean returns, measured in standard deviations. Values: 0.2 = small, 0.5 = medium, 0.8 = large. A d of 0.5 means Q5 averages half a standard deviation higher than Q1.">
      <Var>d</Var> = <Frac num={<><Greek>μ</Greek><Sub>Q5</Sub> − <Greek>μ</Greek><Sub>Q1</Sub></>} den={<><Greek>σ</Greek><Sub>pooled</Sub></>} />
    </Formula>
  ),
  
  SharpeRatio: () => (
    <Formula block compact label="Sharpe Ratio" description="Risk-adjusted return: how much excess return you earn per unit of risk (volatility). Rₚ = portfolio return, Rᶠ = risk-free rate, σₚ = portfolio volatility. Values: 0.5 = decent, 1.0 = good, 2.0 = excellent.">
      <Var>Sharpe</Var> = <Frac num={<><Var>R</Var><Sub>p</Sub> − <Var>R</Var><Sub>f</Sub></>} den={<><Greek>σ</Greek><Sub>p</Sub></>} />
    </Formula>
  ),
  
  TSR: () => (
    <Formula
      block
      compact
      label="Total Shareholder Return"
      description="Conceptual definition: complete return including price appreciation and dividends. In our Tier-1 publication pipeline we approximate TSR by combining split-adjusted close prices with ex-dividend cashflows (dividends are incorporated on ex-dividend dates and reinvested), rather than relying on a vendor dividend-adjusted close series."
    >
      <Var>TSR</Var> = <Frac num={<><Var>P</Var><Sub>end</Sub> − <Var>P</Var><Sub>start</Sub> + Div</>} den={<><Var>P</Var><Sub>start</Sub></>} />
    </Formula>
  ),
  
  Annualized: () => (
    <Formula block compact label="Annualized Return" description="Converts multi-year cumulative return to an equivalent annual rate. Rₐₙₙ = annualized return, Rₒᵤₘ = cumulative return, n = number of years. Example: 100% cumulative over 10 years = 7.2% annualized.">
      <Var>R</Var><Sub>ann</Sub> = (1 + <Var>R</Var><Sub>cum</Sub>)<Sup>1/n</Sup> − 1
    </Formula>
  ),

  Cumulative: () => (
    <Formula block compact label="Cumulative Return" description="Total compounded return over multiple periods. The product (∏) of (1 + each period's return) minus 1. Example: three years of +10%, +5%, -3% = (1.10)(1.05)(0.97) - 1 = 12.0% cumulative.">
      <Var>R</Var><Sub>cum</Sub> = ∏(1 + <Var>r</Var><Sub>t</Sub>) − 1
    </Formula>
  ),
  
  NullHypothesis: () => (
    <Formula block compact label="H₀ (Null Hypothesis)" description="The hypothesis we're testing against: all quintile effects are zero (no relationship between R&D and returns). If we reject this, we have evidence that R&D quintile membership predicts returns.">
      <Greek>α</Greek><Sub>1</Sub> = <Greek>α</Greek><Sub>2</Sub> = <Greek>α</Greek><Sub>3</Sub> = <Greek>α</Greek><Sub>4</Sub> = <Greek>α</Greek><Sub>5</Sub> = 0
    </Formula>
  ),
  
  AltHypothesis: () => (
    <Formula block compact label="H₁ (Alternative Hypothesis)" description="What we conclude if we reject the null: at least one quintile has a different average return. This doesn't tell us which quintile or the direction; that comes from examining the data.">
      At least one <Greek>α</Greek><Sub>i</Sub> ≠ 0
    </Formula>
  ),

  NeweyWest: () => (
    <Formula block compact label="Newey-West Standard Error" description="Corrects standard errors for autocorrelation (returns in year t may be correlated with year t+1) and heteroskedasticity (variance changes over time). Without this correction, t-statistics would be overstated.">
      <Var>SE</Var><Sub>HAC</Sub> = √(<Var>Var</Var> + 2×<Var>Cov</Var><Sub>lag1</Sub>)
    </Formula>
  ),

  HMLPremium: () => (
    <Formula block compact label="HML Premium (High-Minus-Low)" description="The return spread between high-R&D (Q5) and low-R&D (Q1) portfolios. A positive HML means high-R&D stocks outperformed. This is the core metric for testing whether R&D predicts returns.">
      <Var>HML</Var> = <Var>R</Var><Sub>Q5</Sub> − <Var>R</Var><Sub>Q1</Sub>
    </Formula>
  ),

  Turnover: () => (
    <Formula block compact label="Portfolio Turnover" description="Measures how much the portfolio changes at rebalancing. 0.5 × sum of absolute weight changes. 40% turnover means 40% of positions are replaced annually. Higher turnover = higher trading costs.">
      <Var>Turnover</Var> = 0.5 × Σ |<Var>w</Var><Sub>t</Sub> − <Var>w</Var><Sub>t-1</Sub>|
    </Formula>
  ),

  TradingCost: () => (
    <Formula block compact label="Annual Trading Cost" description="Total cost of implementing the strategy. Combines bid-ask spread, market impact, and commissions, multiplied by turnover. For S&P 500 stocks with annual rebalancing, typically 0.05-0.10% per year.">
      <Var>Cost</Var><Sub>ann</Sub> = 2 × (<Var>Spread</Var> + <Var>Impact</Var> + <Var>Commission</Var>) × <Var>Turnover</Var>
    </Formula>
  ),

  FactorAlpha: () => (
    <Formula block compact label="Factor Model Alpha" description="The return component not explained by factor exposures. α is the intercept, β's are factor loadings. A significant positive alpha means the R&D premium is distinct from known factors.">
      <Var>R</Var><Sub>HML-RD</Sub> = <Greek>α</Greek> + <Greek>β</Greek><Sub>MKT</Sub><Var>MKT</Var> + <Greek>β</Greek><Sub>SMB</Sub><Var>SMB</Var> + <Greek>β</Greek><Sub>HML</Sub><Var>HML</Var> + <Greek>ε</Greek>
    </Formula>
  ),

  MaxDrawdown: () => (
    <Formula block compact label="Maximum Drawdown" description="Largest peak-to-trough decline in portfolio value. Shows worst-case loss if you bought at the top and sold at the bottom. A -30% max drawdown means the portfolio fell 30% from its peak at some point.">
      <Var>MDD</Var> = max<Sub>t</Sub>(<Var>Peak</Var><Sub>t</Sub> − <Var>Value</Var><Sub>t</Sub>) / <Var>Peak</Var><Sub>t</Sub>
    </Formula>
  ),
}

export default Formula

