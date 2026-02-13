/**
 * PATH: src/hooks/useResearchData.ts
 * PURPOSE: Data-fetching hook for the Research page — queries, derived state, formatters, exporters
 * WHY: Extracted from Research.tsx to keep the page component under 300 lines
 * DEPENDENCIES:
 *   - @tanstack/react-query: data fetching
 *   - @/lib/api: API client
 *   - @/lib/export: CSV export utility
 */

import { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { exportToCSV } from "@/lib/export"

/** Colors for quintile badges/charts — works in both light and dark modes */
export const QUINTILE_COLORS = ["#dc2626", "#ea580c", "#ca8a04", "#16a34a", "#2563eb"]

export function useResearchData() {
  const [selectedWindow, setSelectedWindow] = useState<string>("5yr")
  const [chartsReady, setChartsReady] = useState(false)
  const [activeTab, setActiveTab] = useState("quintiles")

  // Delay chart rendering to ensure container dimensions are calculated
  // Reset and delay when tab changes to prevent -1 dimension errors
  useEffect(() => {
    setChartsReady(false)
    const timer = setTimeout(() => setChartsReady(true), 150)
    return () => clearTimeout(timer)
  }, [activeTab])

  // ── Queries ───────────────────────────────────────────────────────────────

  const { data: cohortSummary, isLoading: loadingSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: api.getCohortSummary,
  })

  const { data: quintilePerf, isLoading: loadingQuintile } = useQuery({
    queryKey: ["quintilePerf", selectedWindow],
    queryFn: () => api.getQuintilePerformance(selectedWindow),
  })

  const { data: factorPremiumsRaw, isLoading: loadingPremiums } = useQuery({
    queryKey: ["factorPremiums"],
    queryFn: api.getFactorPremiums,
  })

  // Filter out current year (incomplete data)
  const factorPremiums = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return (factorPremiumsRaw || []).filter(f => f.year < currentYear)
  }, [factorPremiumsRaw])

  const { data: aggregateAnova, isLoading: loadingAnova } = useQuery({
    queryKey: ["aggregateAnova"],
    queryFn: api.getAggregateAnova,
  })

  const { data: cohortCompanies, isLoading: loadingCompanies } = useQuery({
    queryKey: ["cohort500", selectedWindow],
    queryFn: () => api.getCohort500(selectedWindow),
  })

  const { data: rollingWindows } = useQuery({
    queryKey: ["rollingWindows", selectedWindow],
    queryFn: () => api.getRollingWindows(selectedWindow),
  })

  // ── Formatters ────────────────────────────────────────────────────────────

  const formatPercent = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "..."
    return `${val >= 0 ? "+" : ""}${val.toFixed(1)}%`
  }

  const formatPValue = (p: number | null | undefined) => {
    if (p === null || p === undefined) return "..."
    if (p < 0.001) return "<0.001***"
    if (p < 0.01) return `${p.toFixed(3)}**`
    if (p < 0.05) return `${p.toFixed(3)}*`
    return p.toFixed(3)
  }

  // ── Export handlers ───────────────────────────────────────────────────────

  const handleExportCohort = () => {
    if (!cohortCompanies || cohortCompanies.length === 0) return

    exportToCSV(
      cohortCompanies.map((c) => ({
        symbol: c.symbol,
        name: c.name || "",
        sector: c.sector || "",
        avg_rd_intensity: c.avg_rd_intensity?.toFixed(2) || "",
        rd_profile: c.rd_profile || "",
        data_quality_score: c.data_quality_score?.toFixed(2) || "",
        years_with_data: c.years_with_data || 0,
      })),
      `research_cohort_${selectedWindow}_${new Date().toISOString().split("T")[0]}.csv`,
      [
        { key: "symbol", header: "Symbol" },
        { key: "name", header: "Company Name" },
        { key: "sector", header: "Sector" },
        { key: "avg_rd_intensity", header: "Avg R&D Intensity (%)" },
        { key: "rd_profile", header: "R&D Profile" },
        { key: "data_quality_score", header: "Data Quality Score" },
        { key: "years_with_data", header: "Years with Data" },
      ]
    )
  }

  const handleExportQuintiles = () => {
    if (!quintilePerf || quintilePerf.length === 0) return

    exportToCSV(
      quintilePerf.map((q: { label: string; avg_rd_intensity?: number; avg_return?: number; volatility?: number; sharpe?: number; num_companies?: number }) => ({
        quintile: q.label,
        avg_rd_intensity: q.avg_rd_intensity?.toFixed(2) || "",
        avg_return: q.avg_return?.toFixed(2) || "",
        volatility: q.volatility?.toFixed(2) || "",
        sharpe: q.sharpe?.toFixed(3) || "",
        num_companies: q.num_companies || 0,
      })),
      `quintile_performance_${selectedWindow}_${new Date().toISOString().split("T")[0]}.csv`,
      [
        { key: "quintile", header: "Quintile" },
        { key: "avg_rd_intensity", header: "Avg R&D Intensity (%)" },
        { key: "avg_return", header: "Avg Return (%)" },
        { key: "volatility", header: "Volatility (%)" },
        { key: "sharpe", header: "Sharpe Ratio" },
        { key: "num_companies", header: "# Companies" },
      ]
    )
  }

  // ── Derived ───────────────────────────────────────────────────────────────

  const isLoading = loadingSummary || loadingQuintile || loadingPremiums || loadingAnova

  return {
    selectedWindow,
    setSelectedWindow,
    chartsReady,
    activeTab,
    setActiveTab,
    cohortSummary,
    quintilePerf,
    factorPremiums,
    aggregateAnova,
    cohortCompanies,
    loadingCompanies,
    rollingWindows,
    isLoading,
    formatPercent,
    formatPValue,
    handleExportCohort,
    handleExportQuintiles,
  }
}
