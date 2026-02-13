/**
 * PATH: frontend/src/pages/papers/Paper2.tsx
 * PURPOSE: Industry-Specific R&D Investment Patterns - Academic paper format
 * ROLE IN ARCHITECTURE: Research paper page with cross-sector analysis
 * MAIN EXPORTS: Paper2 component
 * NON-RESPONSIBILITIES: Does not handle data fetching logic
 * NOTES FOR FUTURE AI: Follows standard academic paper structure with 10 sections.
 *   JSX split into sub-components under src/components/paper2/.
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect, useMemo } from "react"
import { api } from "@/lib/api"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { cn } from "@/lib/utils"
import {
  Paper2FrontMatter,
  Paper2Methods,
  Paper2Results,
  Paper2BackMatter,
} from "@/components/paper2"

const SECTOR_COLORS: Record<string, string> = {
  "Technology": "#3b82f6",
  "Healthcare": "#22c55e",
  "Consumer Cyclical": "#f59e0b",
  "Financial Services": "#8b5cf6",
  "Industrials": "#6366f1",
  "Communication Services": "#ec4899",
  "Consumer Defensive": "#14b8a6",
  "Energy": "#ef4444",
  "Basic Materials": "#84cc16",
  "Real Estate": "#06b6d4",
  "Utilities": "#64748b",
}

// Table of contents sections
const sections = [
  { id: "abstract", label: "Abstract" },
  { id: "introduction", label: "1. Introduction" },
  { id: "literature", label: "2. Literature Review" },
  { id: "data", label: "3. Data & Sample" },
  { id: "methodology", label: "4. Methodology" },
  { id: "results", label: "5. Results" },
  { id: "discussion", label: "6. Discussion" },
  { id: "conclusion", label: "7. Conclusion" },
  { id: "replicability", label: "8. Replicability" },
  { id: "references", label: "References" },
]

export function Paper2() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // Intersection observer for active section tracking
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id)
          }
        })
      },
      { rootMargin: "-20% 0px -60% 0px" }
    )

    sections.forEach(({ id }) => {
      const element = document.getElementById(id)
      if (element) observer.observe(element)
    })

    return () => observer.disconnect()
  }, [])

  const scrollToSection = (id: string) => {
    const element = document.getElementById(id)
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" })
    }
  }

  const { data: rdBySector } = useQuery({
    queryKey: ["rdBySector"],
    queryFn: () => api.getRDBySector(),
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  const { data: rdLeaders } = useQuery({
    queryKey: ["rdLeaders"],
    queryFn: () => api.getRDLeaderboard(100),
  })

  const { data: rdTrends } = useQuery({
    queryKey: ["rdTrends"],
    queryFn: () => api.getRDTrends(),
  })

  const rdSampleYearRange = useMemo(() => {
    const years = (rdTrends || []).map((r: any) => r.year).filter((y: any): y is number => typeof y === "number")
    if (years.length === 0) return undefined
    const min = Math.min(...years)
    const max = Math.max(...years)
    if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined
    return `${min}-${max}`
  }, [rdTrends])

  // Format sector data for charts
  const sectorData = (rdBySector || []).map((s: any) => ({
    ...s,
    fill: SECTOR_COLORS[s.sector] || "#64748b",
    totalRdB: s.total_rd_spend / 1e9,
  })).sort((a: any, b: any) => b.avg_rd_intensity - a.avg_rd_intensity)

  // Sector by coverage
  const sectorCoverageData = (cohortSummary?.by_sector || []).map((s: any) => ({
    sector: s.sector,
    total: s.total,
    n_5yr: s.n_5yr,
    n_10yr: s.n_10yr,
    n_20yr: s.n_20yr,
    coverage_5yr: Math.round((s.n_5yr / s.total) * 100),
    coverage_10yr: Math.round((s.n_10yr / s.total) * 100),
    coverage_20yr: Math.round((s.n_20yr / s.total) * 100),
    fill: SECTOR_COLORS[s.sector] || "#64748b",
  }))

  // Leaders by sector
  const leadersBySector = (rdLeaders || []).reduce((acc: any, leader: any) => {
    const sector = leader.sector || "Other"
    if (!acc[sector]) acc[sector] = []
    acc[sector].push(leader)
    return acc
  }, {} as Record<string, any>)

  // Radar chart data for top sectors
  const radarData = sectorData.slice(0, 8).map((s: any) => ({
    sector: s.sector.length > 15 ? s.sector.substring(0, 12) + "..." : s.sector,
    fullSector: s.sector,
    intensity: s.avg_rd_intensity,
    companies: s.company_count,
    spend: Math.min(s.totalRdB, 100),
  }))

  // Key metrics for the right sidebar
  const keyMetrics = [
    { label: "Top Sector", value: sectorData[0]?.sector?.substring(0, 10) || "Healthcare", color: "text-blue-600 dark:text-blue-400" },
    { label: "Total R&D", value: `$${sectorData.reduce((acc: number, s: any) => acc + s.totalRdB, 0).toFixed(0)}B`, color: "text-green-600 dark:text-emerald-400" },
    { label: "Sectors Analyzed", value: `${sectorData.length}`, color: "text-foreground" },
    { label: "Sample Size", value: `${cohortSummary?.total_companies || "..."}`, color: "text-foreground" },
  ]

  const handleDownload = () => {
    document.body.classList.add('printing-paper')
    window.print()
    setTimeout(() => {
      document.body.classList.remove('printing-paper')
    }, 1000)
  }

  return (
    <div className="flex gap-8">
      {/* Main Content - expands when right nav is collapsed */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        <Paper2FrontMatter
          cohortSummary={cohortSummary}
          sectorData={sectorData}
          rdSampleYearRange={rdSampleYearRange}
          handleDownload={handleDownload}
        />

        <Paper2Methods
          cohortSummary={cohortSummary}
          sectorData={sectorData}
          sectorCoverageData={sectorCoverageData}
          rdSampleYearRange={rdSampleYearRange}
        />

        <Paper2Results
          sectorData={sectorData}
          radarData={radarData}
          leadersBySector={leadersBySector}
        />

        <Paper2BackMatter />
      </div>

      {/* Right Sidebar - Table of Contents */}
      <RightTableOfContents
        sections={sections}
        activeSection={activeSection}
        onSectionClick={scrollToSection}
        keyMetrics={keyMetrics}
        onCollapseChange={setRightNavCollapsed}
      />
    </div>
  )
}

export default Paper2
