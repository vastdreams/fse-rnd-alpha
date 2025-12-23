/**
 * PATH: frontend/src/components/Formula.tsx
 * PURPOSE: Renders mathematical formulas with proper formatting (subscripts, superscripts, Greek letters)
 */

import { cn } from "@/lib/utils"

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
          <p className={cn(
            "font-medium text-muted-foreground uppercase tracking-wider",
            compact ? "text-[10px] mb-1" : "text-xs mb-2"
          )}>{label}</p>
        )}
        <div className={cn(
          "font-serif italic text-emerald-500 dark:text-emerald-400",
          compact ? "text-base" : "text-lg"
        )}>
          {children}
        </div>
        {description && (
          <p className="text-xs text-muted-foreground mt-2">{description}</p>
        )}
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

// Pre-defined common formulas
export const Formulas = {
  RDIntensity: () => (
    <Formula block compact>
      <Var>R&D Intensity</Var> = <Frac num="R&D Expense" den="Revenue" /> × 100%
    </Formula>
  ),
  
  ANOVA: () => (
    <Formula block compact label="ANOVA Model">
      <Var>Return</Var><Sub>ij</Sub> = <Greek>μ</Greek> + <Greek>α</Greek><Sub>i</Sub> + <Greek>ε</Greek><Sub>ij</Sub>
      <span className="text-xs text-muted-foreground ml-3 not-italic font-sans">
        (α<Sub>i</Sub> = quintile effect)
      </span>
    </Formula>
  ),
  
  EtaSquared: () => (
    <Formula block compact label="η² (Effect Size)">
      <Greek>η</Greek><Sup>2</Sup> = <Frac num={<>SS<Sub>between</Sub></>} den={<>SS<Sub>total</Sub></>} />
    </Formula>
  ),
  
  CohensD: () => (
    <Formula block compact label="Cohen's d">
      <Var>d</Var> = <Frac num={<><Greek>μ</Greek><Sub>Q5</Sub> − <Greek>μ</Greek><Sub>Q1</Sub></>} den={<><Greek>σ</Greek><Sub>pooled</Sub></>} />
    </Formula>
  ),
  
  SharpeRatio: () => (
    <Formula block compact label="Sharpe Ratio">
      <Var>Sharpe</Var> = <Frac num={<><Var>R</Var><Sub>p</Sub> − <Var>R</Var><Sub>f</Sub></>} den={<><Greek>σ</Greek><Sub>p</Sub></>} />
    </Formula>
  ),
  
  TSR: () => (
    <Formula block compact label="Total Shareholder Return">
      <Var>TSR</Var> = <Frac num={<><Var>P</Var><Sub>end</Sub> − <Var>P</Var><Sub>start</Sub> + Div</>} den={<><Var>P</Var><Sub>start</Sub></>} />
    </Formula>
  ),
  
  Annualized: () => (
    <Formula block compact label="Annualized">
      <Var>R</Var><Sub>ann</Sub> = (1 + <Var>R</Var><Sub>cum</Sub>)<Sup>1/n</Sup> − 1
    </Formula>
  ),

  Cumulative: () => (
    <Formula block compact label="Cumulative">
      <Var>R</Var><Sub>cum</Sub> = ∏(1 + <Var>r</Var><Sub>t</Sub>) − 1
    </Formula>
  ),
  
  NullHypothesis: () => (
    <Formula block compact label="H₀">
      <Greek>α</Greek><Sub>1</Sub> = <Greek>α</Greek><Sub>2</Sub> = <Greek>α</Greek><Sub>3</Sub> = <Greek>α</Greek><Sub>4</Sub> = <Greek>α</Greek><Sub>5</Sub> = 0
    </Formula>
  ),
  
  AltHypothesis: () => (
    <Formula block compact label="H₁">
      At least one <Greek>α</Greek><Sub>i</Sub> ≠ 0
    </Formula>
  ),
}

export default Formula

