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
import { METRIC_EXPLANATIONS } from "./InfoTooltipData"

// Re-export so existing consumers can still import from this file
export { METRIC_EXPLANATIONS } from "./InfoTooltipData"

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
