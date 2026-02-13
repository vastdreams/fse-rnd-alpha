/**
 * PATH: frontend/src/pages/Documentation.tsx
 * PURPOSE:
 *   - Provide an index of research outputs (Main Paper + Sub-Research) and platform documentation.
 *
 * ROLE IN ARCHITECTURE:
 *   - Frontend documentation hub and navigation entrypoint for research artifacts.
 *
 * MAIN EXPORTS:
 *   - Documentation: route component for /documentation
 *
 * NON-RESPONSIBILITIES:
 *   - Does not compute research metrics (backend does).
 *   - Does not hardcode unverifiable research results ("0 hallucinations" policy).
 *
 * NOTES FOR FUTURE AI:
 *   - Any numeric claims displayed here should come from API responses.
 *   - Prefer linking to the Main Paper page for citation-ready narrative.
 *   - Tab content extracted into src/components/documentation/ for 300-line rule.
 */

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/lib/api"
import {
  PapersTab,
  OverviewTab,
  MetricsTab,
  DashboardsTab,
  AnalysisTab,
  PortfolioTab,
  InterpretationTab,
} from "@/components/documentation"

export function Documentation() {
  // "0 hallucinations" policy: show headline numbers only from API.
  const { data: aggregateAnova } = useQuery({
    queryKey: ["aggregateAnova", "documentation"],
    queryFn: () => api.getAggregateAnova(),
  })

  const { data: annualHml } = useQuery({
    queryKey: ["annualHmlPremium", "documentation"],
    queryFn: () => api.getAnnualHmlPremium(),
  })

  const { data: rdBySector } = useQuery({
    queryKey: ["rdBySector", "documentation"],
    queryFn: () => api.getRDBySector(),
  })

  const { data: fmpOverview } = useQuery({
    queryKey: ["fmpOverview", "documentation"],
    queryFn: () => api.getFMPOverview(),
  })

  const periodLabel = useMemo(() => {
    const rows = annualHml?.annual_premiums
    if (!rows || rows.length === 0) return "..."
    const first = rows[0]?.year
    const last = rows[rows.length - 1]?.year
    if (!first || !last) return "..."
    return `${first} to ${last}`
  }, [annualHml])

  const premium5yr = aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference
  const premium10yr = aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference
  const premium20yr = aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference
  const eta5yr = aggregateAnova?.["5yr"]?.anova?.eta_squared
  const eta20yr = aggregateAnova?.["20yr"]?.anova?.eta_squared

  const topSector = useMemo(() => {
    const rows = (rdBySector || []).slice().sort((a, b) => b.avg_rd_intensity - a.avg_rd_intensity)
    return rows[0]
  }, [rdBySector])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Papers & Documentation</h1>
        <p className="text-muted-foreground">
          Research papers and complete guide to the R&D Factor Analysis Platform
        </p>
      </div>

      <Tabs defaultValue="papers" className="space-y-4">
        <TabsList className="grid w-full grid-cols-7">
          <TabsTrigger value="papers">Papers</TabsTrigger>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="dashboards">Dashboards</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="portfolio">Portfolio</TabsTrigger>
          <TabsTrigger value="interpretation">Interpretation</TabsTrigger>
        </TabsList>
        
        <TabsContent value="papers" className="space-y-6">
          <PapersTab
            premium5yr={premium5yr}
            premium10yr={premium10yr}
            premium20yr={premium20yr}
            eta5yr={eta5yr}
            eta20yr={eta20yr}
            topSector={topSector}
          />
        </TabsContent>

        <TabsContent value="overview" className="space-y-4">
          <OverviewTab
            fmpOverview={fmpOverview}
            periodLabel={periodLabel}
            eta5yr={eta5yr}
            eta20yr={eta20yr}
          />
        </TabsContent>

        <TabsContent value="metrics" className="space-y-4">
          <MetricsTab />
        </TabsContent>

        <TabsContent value="dashboards" className="space-y-4">
          <DashboardsTab />
        </TabsContent>

        <TabsContent value="analysis" className="space-y-4">
          <AnalysisTab
            premium5yr={premium5yr}
            premium20yr={premium20yr}
            eta5yr={eta5yr}
            eta20yr={eta20yr}
            aggregateAnova={aggregateAnova}
          />
        </TabsContent>

        <TabsContent value="portfolio" className="space-y-4">
          <PortfolioTab />
        </TabsContent>

        <TabsContent value="interpretation" className="space-y-4">
          <InterpretationTab
            premium5yr={premium5yr}
            premium20yr={premium20yr}
            eta5yr={eta5yr}
            eta20yr={eta20yr}
            periodLabel={periodLabel}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default Documentation
