/**
 * PATH: frontend/src/pages/papers/Paper4.tsx
 * PURPOSE: Fundamental Value Creation Through R&D - Academic paper on operational value
 * WHY: Research paper page with fundamental analysis; layout + data in parent, sections in sub-components
 * FLOW:
 * ┌──────────┐ ┌──────────────────┐ ┌──────────────────┐
 * │ API Data │ → │ Paper4 (parent)  │ → │ Sub-components   │
 * └──────────┘ └──────────────────┘ └──────────────────┘
 * DEPENDENCIES:
 * - @tanstack/react-query: data fetching
 * - paper4 sub-components: section rendering
 * - RightTableOfContents: sidebar navigation
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { cn } from "@/lib/utils"
import {
  Paper4FrontMatter,
  Paper4Methods,
  Paper4Results,
  Paper4BackMatter,
} from "@/components/paper4"

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

export function Paper4() {
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

  const { data: rdTrends } = useQuery({
    queryKey: ["rdTrends"],
    queryFn: () => api.getRDTrends(),
  })

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
    queryFn: () => api.getRDLeaderboard(20),
  })

  // R&D trends over time
  const trendData = (rdTrends || []).map((t: any) => ({
    year: t.year,
    companies: t.companies,
    avgIntensity: t.avg_rd_intensity,
    totalSpendB: t.total_rd_spend / 1e9,
  }))

  // Calculate aggregate metrics
  const totalRdSpend = rdBySector?.reduce((acc: number, s: any) => acc + s.total_rd_spend, 0) || 0
  const avgIntensity = cohortSummary?.avg_rd_intensity || 0

  // Key metrics for the right sidebar
  const keyMetrics = [
    { label: "Total R&D", value: `$${(totalRdSpend / 1e12).toFixed(1)}T`, color: "text-amber-600 dark:text-amber-400" },
    { label: "Avg Intensity", value: `${avgIntensity.toFixed(1)}%`, color: "text-green-600 dark:text-emerald-400" },
    { label: "Companies", value: `${cohortSummary?.total_companies || "..."}`, color: "text-foreground" },
    { label: "Years", value: `${trendData.length}`, color: "text-foreground" },
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
        <Paper4FrontMatter
          totalRdSpend={totalRdSpend}
          cohortSummary={cohortSummary}
          trendData={trendData}
          handleDownload={handleDownload}
        />

        <Paper4Methods
          totalRdSpend={totalRdSpend}
          avgIntensity={avgIntensity}
          cohortSummary={cohortSummary}
          trendData={trendData}
        />

        <Paper4Results
          trendData={trendData}
          rdLeaders={rdLeaders}
        />

        <Paper4BackMatter />
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

export default Paper4
