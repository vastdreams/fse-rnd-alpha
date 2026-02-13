/**
 * PATH: frontend/src/pages/Overview.tsx
 * PURPOSE: Landing page summarizing the R&D factor research and dataset coverage.
 * WHY: Orchestrates sub-components; keeps hooks in parent per project convention.
 *
 * NOTES FOR FUTURE AI:
 *   - Any numeric claim on this page should be rendered from API endpoints.
 *   - Avoid strong guarantee language; keep claims as dataset-conditional.
 */

import { useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { HeroSection, DatasetOverview, SectorLeadersReturns } from "@/components/overview"

export function Overview() {
  const { data: aggregateAnova, isLoading: loadingAnova } = useQuery({
    queryKey: ["aggregateAnova", "overview"],
    queryFn: api.getAggregateAnova,
  })

  const { data: annualHml, isLoading: loadingHml } = useQuery({
    queryKey: ["annualHmlPremium", "overview"],
    queryFn: api.getAnnualHmlPremium,
  })

  const returnPeriodLabel = useMemo(() => {
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

  const compoundingMultiplier10y = useMemo(() => {
    if (premium5yr === undefined) return null
    return Math.pow(1 + premium5yr / 100, 10)
  }, [premium5yr])
  
  const { data: overview, isLoading: loadingOverview } = useQuery({
    queryKey: ["fmpOverview"],
    queryFn: api.getFMPOverview,
  })

  const { data: rdTrends, isLoading: loadingTrends } = useQuery({
    queryKey: ["rdTrends"],
    queryFn: api.getRDTrends,
  })

  const { data: rdBySector, isLoading: loadingSectors } = useQuery({
    queryKey: ["rdBySector"],
    queryFn: api.getRDBySector,
  })

  const { data: rdLeaders, isLoading: loadingLeaders } = useQuery({
    queryKey: ["rdLeaderboard"],
    queryFn: () => api.getRDLeaderboard(10),
  })

  const { data: returnsSummary, isLoading: loadingReturns } = useQuery({
    queryKey: ["returnsSummary"],
    queryFn: api.getReturnsSummary,
  })

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "..."
    if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(1)}M`
    return num.toLocaleString()
  }

  const isLoading = loadingOverview || loadingTrends || loadingSectors || loadingLeaders || loadingReturns || loadingAnova || loadingHml

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <HeroSection
        overview={overview}
        returnPeriodLabel={returnPeriodLabel}
        premium5yr={premium5yr}
        premium10yr={premium10yr}
        premium20yr={premium20yr}
        compoundingMultiplier10y={compoundingMultiplier10y}
      />

      <DatasetOverview overview={overview} rdTrends={rdTrends} />

      <SectorLeadersReturns
        overview={overview}
        rdBySector={rdBySector}
        rdLeaders={rdLeaders}
        returnsSummary={returnsSummary}
        formatNumber={formatNumber}
      />
    </div>
  )
}
