/**
 * PATH: frontend/src/components/RightTableOfContents.tsx
 * PURPOSE: Collapsible right-side table of contents navigation for academic papers
 * ROLE IN ARCHITECTURE: UI component for paper navigation
 * MAIN EXPORTS:
 *   - RightTableOfContents: Collapsible ToC component
 *   - Section: Type definition for ToC sections
 * NON-RESPONSIBILITIES:
 *   - Does not manage paper content
 *   - Does not handle paper data fetching
 * NOTES FOR FUTURE AI:
 *   - Uses sticky positioning (not fixed) so main content expands naturally
 *   - When collapsed, shows only a thin strip with toggle button
 *   - The collapse state is passed up to parent via optional callback
 */

import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight, List } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export interface Section {
  id: string
  label: string
}

interface KeyMetric {
  label: string
  value: string
  color?: string
}

interface RightTableOfContentsProps {
  sections: Section[]
  activeSection: string
  onSectionClick: (id: string) => void
  keyMetrics?: KeyMetric[]
  className?: string
  onCollapseChange?: (collapsed: boolean) => void
}

export function RightTableOfContents({
  sections,
  activeSection,
  onSectionClick,
  keyMetrics,
  className,
  onCollapseChange,
}: RightTableOfContentsProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [userToggled, setUserToggled] = useState(false)

  // Handle responsive auto-collapse (only on initial load, not after user toggle)
  useEffect(() => {
    const handleResize = () => {
      // Only auto-collapse if user hasn't manually toggled
      if (!userToggled) {
        const shouldCollapse = window.innerWidth < 1280
        setCollapsed(shouldCollapse)
        onCollapseChange?.(shouldCollapse)
      }
    }

    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [onCollapseChange, userToggled])

  const handleToggle = () => {
    setUserToggled(true) // Mark that user has manually toggled
    const newCollapsed = !collapsed
    setCollapsed(newCollapsed)
    onCollapseChange?.(newCollapsed)
  }

  return (
    <div
      className={cn(
        "hidden lg:flex flex-shrink-0 transition-all duration-300 ease-in-out",
        collapsed ? "w-12" : "w-64",
        className
      )}
    >
      {/* Sticky container for the navigation */}
      <div className="sticky top-24 w-full">
        {/* Collapse Toggle Button */}
        <div className="relative h-0 overflow-visible">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleToggle}
                  className={cn(
                    // Keep the toggle outside the scroll container so it never gets clipped.
                    "absolute -left-3 top-1 w-6 h-6 rounded-full border border-border bg-card p-0 shadow-md z-20 hover:bg-muted"
                  )}
                >
                  {collapsed ? (
                    <ChevronLeft className="h-3 w-3" />
                  ) : (
                    <ChevronRight className="h-3 w-3" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="left">
                {collapsed ? "Expand navigation" : "Collapse navigation"}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>

        {/* Content */}
        <div className="w-full max-h-[calc(100vh-8rem)] overflow-y-auto scrollbar-thin scrollbar-thumb-border scrollbar-track-transparent">
          {collapsed ? (
            /* Collapsed State - Mini navigation dots */
            <TooltipProvider delayDuration={0}>
              <div className="flex flex-col items-center gap-2 pt-8 px-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="p-2 rounded-lg bg-card/80 backdrop-blur border border-border/50 mb-2 cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors duration-200">
                      <List className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="left">
                    <span className="font-medium">Table of Contents</span>
                  </TooltipContent>
                </Tooltip>
                
                {sections.map(({ id, label }) => (
                  <Tooltip key={id}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => onSectionClick(id)}
                        className={cn(
                          "w-2.5 h-2.5 rounded-full transition-all duration-200 cursor-pointer",
                          activeSection === id
                            ? "bg-primary scale-125 shadow-sm"
                            : "bg-muted-foreground/30 hover:bg-primary/60 hover:scale-110"
                        )}
                      />
                    </TooltipTrigger>
                    <TooltipContent side="left" className="font-medium">
                      {label}
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </TooltipProvider>
          ) : (
            /* Expanded State - Full navigation */
            <div className="space-y-4 pl-2">
              {/* Table of Contents */}
              <Card className="bg-card/80 backdrop-blur border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    On This Page
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <nav className="space-y-1">
                    {sections.map(({ id, label }) => (
                      <button
                        key={id}
                        onClick={() => onSectionClick(id)}
                        className={cn(
                          "block w-full text-left px-3 py-2 text-sm rounded-lg transition-all duration-200 cursor-pointer relative",
                          activeSection === id
                            ? "bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium border-l-2 border-blue-500 pl-2.5"
                            : "text-muted-foreground hover:text-foreground hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:pl-3.5"
                        )}
                      >
                        {label}
                      </button>
                    ))}
                  </nav>
                </CardContent>
              </Card>

              {/* Key Metrics */}
              {keyMetrics && keyMetrics.length > 0 && (
                <Card className="bg-card/80 backdrop-blur border-border/50">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-muted-foreground">
                      Key Metrics
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0 space-y-3">
                    {keyMetrics.map((metric, index) => (
                      <div key={index} className="flex justify-between items-baseline gap-3 text-sm">
                        <span className="text-muted-foreground shrink-0">{metric.label}</span>
                        <span
                          className={cn(
                            "font-mono text-right",
                            metric.color || "text-foreground"
                          )}
                        >
                          {metric.value}
                        </span>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
