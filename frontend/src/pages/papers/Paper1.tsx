/**
 * PATH: frontend/src/pages/papers/Paper1.tsx
 * PURPOSE:
 *   - Sub-Research 1 deep dive: returns + inference visuals for the R&D intensity premium.
 *
 * ROLE IN ARCHITECTURE:
 *   - Research communication layer (frontend). Renders charts/tables from backend APIs.
 *   - Parent component: owns data fetching, state, and layout. Delegates sections to sub-components.
 *
 * MAIN EXPORTS:
 *   - Paper1: Sub-Research 1 page component
 *
 * NON-RESPONSIBILITIES:
 *   - Does not compute metrics (backend does).
 *   - Does not hardcode unverifiable result numbers ("0 hallucinations" policy).
 *
 * NOTES FOR FUTURE AI:
 *   - Keep numeric claims sourced from API responses (aggregate ANOVA, annual HML, rolling windows).
 *   - Avoid hardcoding external-literature numeric claims unless independently verified and cited.
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect, useMemo } from "react"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import {
  Paper1FrontMatter,
  Paper1Methods,
  Paper1Results,
  Paper1BackMatter,
} from "@/components/paper1"

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

export function Paper1() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // Print/PDF export handler
  const handlePrintPDF = () => {
    // Add print class to body for print-specific styling
    document.body.classList.add('printing-paper')
    window.print()
    // Remove class after print dialog closes
    setTimeout(() => {
      document.body.classList.remove('printing-paper')
    }, 1000)
  }

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

  // Fetch data
  const { data: quintilePerf5yr } = useQuery({
    queryKey: ["quintilePerf", "5yr"],
    queryFn: () => api.getQuintilePerformance("5yr"),
  })

  useQuery({
    queryKey: ["quintilePerf", "20yr"],
    queryFn: () => api.getQuintilePerformance("20yr"),
  })

  const { data: aggregateAnova } = useQuery({
    queryKey: ["aggregateAnova"],
    queryFn: () => api.getAggregateAnova(),
  })

  const { data: cohortSummary } = useQuery({
    queryKey: ["cohortSummary"],
    queryFn: () => api.getCohortSummary(),
  })

  const { data: factorPremiumSeries } = useQuery({
    queryKey: ["factorPremiums"],
    queryFn: () => api.getFactorPremiums(),
  })

  const sampleYearRange = useMemo(() => {
    const years = (factorPremiumSeries || []).map((r) => r.year).filter((y): y is number => typeof y === "number")
    if (years.length === 0) return undefined
    const min = Math.min(...years)
    const max = Math.max(...years)
    if (!Number.isFinite(min) || !Number.isFinite(max)) return undefined
    return `${min}-${max}`
  }, [factorPremiumSeries])

  // Key metrics for the right sidebar - dynamically computed from API data
  const rdPremium5yr = aggregateAnova?.["5yr"]?.ttest_high_vs_low?.mean_difference
  const rdPremium10yr = aggregateAnova?.["10yr"]?.ttest_high_vs_low?.mean_difference
  const rdPremium20yr = aggregateAnova?.["20yr"]?.ttest_high_vs_low?.mean_difference
  const etaSquared5yr = aggregateAnova?.["5yr"]?.anova?.eta_squared
  const etaSquared20yr = aggregateAnova?.["20yr"]?.anova?.eta_squared
  const pValue20yr = aggregateAnova?.["20yr"]?.anova?.p_value
  
  const keyMetrics = [
    { 
      label: "R&D Premium", 
      value: rdPremium20yr ? `${rdPremium20yr >= 0 ? "+" : ""}${rdPremium20yr.toFixed(1)}%` : "...", 
      color: "text-green-600 dark:text-emerald-400" 
    },
    { 
      label: "Effect Size (η²)", 
      value: etaSquared20yr ? etaSquared20yr.toFixed(3) : "...", 
      color: "text-blue-600 dark:text-blue-400" 
    },
    { 
      label: "Significance", 
      value: pValue20yr !== undefined ? (pValue20yr < 0.001 ? "p < 0.001" : `p = ${pValue20yr.toFixed(4)}`) : "...", 
      color: "text-green-600 dark:text-emerald-400" 
    },
    { label: "Sample Size", value: `${cohortSummary?.total_companies || "..."}`, color: "text-foreground" },
  ]

  const { data: rollingWindows5yr } = useQuery({
    queryKey: ["rollingWindows", "5yr"],
    queryFn: () => api.getRollingWindows("5yr"),
  })

  // Annual HML Premium - PRIMARY INFERENCE (non-overlapping)
  const { data: annualHmlData, isLoading: annualHmlLoading } = useQuery({
    queryKey: ["annualHmlPremium"],
    queryFn: () => api.getAnnualHmlPremium(),
  })

  const annualMeanPremium = annualHmlData?.mean_premium
  const annualTStat = annualHmlData?.hac_adjusted?.t_statistic
  const annualPValue = annualHmlData?.hac_adjusted?.p_value
  const annualNYears = annualHmlData?.n_years

  const rollingWindowData = (rollingWindows5yr || []).map(w => ({
    period: `${w.start_year}-${w.end_year}`,
    startYear: w.start_year,
    rdPremium: w.rd_premium,
    q1Return: w.quintiles.find((q: { quintile: number }) => q.quintile === 1)?.avg_return || 0,
    q5Return: w.quintiles.find((q: { quintile: number }) => q.quintile === 5)?.avg_return || 0,
  }))

  return (
    <div className="flex gap-8">
      {/* Main Content - expands when right nav is collapsed */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        <Paper1FrontMatter
          sampleYearRange={sampleYearRange}
          cohortSummary={cohortSummary}
          aggregateAnova={aggregateAnova}
          handlePrintPDF={handlePrintPDF}
        />
        <Paper1Methods
          cohortSummary={cohortSummary}
          annualHmlData={annualHmlData}
          rollingWindows5yr={rollingWindows5yr}
        />
        <Paper1Results
          annualHmlData={annualHmlData}
          annualHmlLoading={annualHmlLoading}
          aggregateAnova={aggregateAnova}
          quintilePerf5yr={quintilePerf5yr}
          rollingWindowData={rollingWindowData}
        />
        <Paper1BackMatter
          rdPremium5yr={rdPremium5yr}
          rdPremium10yr={rdPremium10yr}
          rdPremium20yr={rdPremium20yr}
          etaSquared5yr={etaSquared5yr}
          etaSquared20yr={etaSquared20yr}
          annualMeanPremium={annualMeanPremium}
          annualTStat={annualTStat}
          annualPValue={annualPValue}
          annualNYears={annualNYears}
        />
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
