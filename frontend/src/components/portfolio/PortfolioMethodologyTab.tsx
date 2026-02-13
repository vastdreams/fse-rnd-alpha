/** Methodology tab content – selection formula, components, sector constraints. */
import type { PortfolioData } from "@/hooks/usePortfolioData"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { TabsContent } from "@/components/ui/tabs"
import { FlaskConical, BookOpen, ChevronDown, ChevronUp } from "lucide-react"

interface Props {
  data: PortfolioData
  showMethodologyDetails: boolean
  setShowMethodologyDetails: (v: boolean) => void
}

export function PortfolioMethodologyTab({ data, showMethodologyDetails, setShowMethodologyDetails }: Props) {
  const { methodology } = data

  return (
    <TabsContent value="methodology" className="space-y-4">
      <Card className="border-border">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-emerald-500" />
            R&amp;D Alpha Selection Formula
          </CardTitle>
          <CardDescription>Research-based, sector-agnostic scoring methodology</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Main Formula */}
          <div className="bg-slate-900 dark:bg-slate-950 rounded-lg p-6 border border-slate-700">
            <h3 className="text-lg font-semibold text-white mb-4">Selection Formula</h3>
            <div className="text-center">
              <code className="text-xl text-emerald-400 font-mono">
                {methodology?.formula || "R&D Alpha Score = (RD_Intensity × Sector_Adj × Momentum × Quality) / Volatility"}
              </code>
            </div>
          </div>

          {/* Formula Components */}
          <div>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              Formula Components
              <Button variant="ghost" size="sm" onClick={() => setShowMethodologyDetails(!showMethodologyDetails)}>
                {showMethodologyDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              </Button>
            </h3>
            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(methodology?.components || {}).map(([key, description]) => (
                <div key={key} className="bg-muted/50 rounded-lg p-4 border border-border">
                  <div className="font-mono text-sm font-semibold text-emerald-500 mb-2">{key}</div>
                  <div className="text-sm text-muted-foreground">{description as string}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Expanded Details */}
          {showMethodologyDetails && (
            <>
              <div className="border-t border-border pt-6">
                <h3 className="text-lg font-semibold mb-4">Sector Constraints</h3>
                <div className="grid gap-4 md:grid-cols-2">
                  {Object.entries(methodology?.sector_constraints || {}).map(([key, constraint]) => (
                    <div key={key} className="bg-muted/50 rounded-lg p-4 border border-border">
                      <div className="font-semibold text-foreground mb-1">{key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}</div>
                      <div className="text-2xl font-mono text-emerald-500">{((constraint as { value: number }).value * 100).toFixed(0)}%</div>
                      <div className="text-sm text-muted-foreground mt-1">{(constraint as { description: string }).description}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="border-t border-border pt-6">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2"><BookOpen className="w-5 h-5" />Research Foundation</h3>
                <div className="space-y-2">
                  {(methodology?.research_citations || []).map((citation: string, i: number) => (
                    <div key={i} className="flex items-start gap-3 text-sm text-muted-foreground">
                      <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-xs font-bold flex-shrink-0">{i + 1}</div>
                      <span>{citation}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="border-t border-border pt-6">
                <h3 className="text-lg font-semibold mb-4">Model Parameters</h3>
                <div className="grid gap-2 md:grid-cols-3">
                  {Object.entries(methodology?.parameters || {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center bg-muted/30 rounded px-3 py-2">
                      <span className="text-sm text-muted-foreground">{key.replace(/_/g, " ")}</span>
                      <span className="font-mono text-sm text-foreground">{typeof value === "number" ? value.toFixed(2) : value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="text-xs text-muted-foreground text-right">
            Last updated: {methodology?.last_updated || "..."}
          </div>
        </CardContent>
      </Card>
    </TabsContent>
  )
}
