/**
 * PATH: frontend/src/pages/papers/Paper3.tsx
 * PURPOSE: R&D-Sorted Return Premium - Analysis of high-minus-low R&D portfolio returns
 * ROLE IN ARCHITECTURE: Research paper page with factor premium analysis
 * MAIN EXPORTS: Paper3 component
 * WHY: Parent page that owns data fetching, state, and layout; delegates sections to sub-components
 */

import { useQuery } from "@tanstack/react-query"
import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { TrendingUp } from "lucide-react"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { cn } from "@/lib/utils"
import {
  Paper3FrontMatter,
  Paper3Methods,
  Paper3ResultsCharts,
  Paper3ResultsTables,
  Paper3BackMatter,
} from "@/components/paper3"

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

export function Paper3() {
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

  // Publication snapshot (frozen dataset for paper pages)
  const { data: snapshot } = useQuery({
    queryKey: ["publicationSnapshot"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const snapshotPayload = snapshot?.payload

  const factorPremiums = Array.isArray(snapshotPayload?.factor_premiums)
    ? snapshotPayload?.factor_premiums
    : []

  const publicationStats =
    snapshotPayload?.publication_stats && typeof snapshotPayload.publication_stats === "object" && !("error" in snapshotPayload.publication_stats)
      ? snapshotPayload.publication_stats
      : undefined

  const spanningTests =
    snapshotPayload?.spanning_tests_full && typeof snapshotPayload.spanning_tests_full === "object" && !("error" in snapshotPayload.spanning_tests_full)
      ? snapshotPayload.spanning_tests_full
      : undefined

  const mispricingTests =
    snapshotPayload?.mispricing_tests && typeof snapshotPayload.mispricing_tests === "object" && !("error" in snapshotPayload.mispricing_tests)
      ? snapshotPayload.mispricing_tests
      : undefined

  const doubleSortData =
    snapshotPayload?.double_sort_analysis && typeof snapshotPayload.double_sort_analysis === "object" && !("error" in snapshotPayload.double_sort_analysis)
      ? snapshotPayload.double_sort_analysis
      : undefined

  // Format factor premium time series
  const premiumData = (factorPremiums || []).map((f: any) => ({
    year: f.year,
    // NOTE: API returns are already in percent units (e.g., 7.11 means 7.11%).
    rdPremium: f.rd_premium ?? null,
    q1: f.q1_return ?? null,
    q5: f.q5_return ?? null,
    spread: f.q5_return !== null && f.q1_return !== null ? (f.q5_return - f.q1_return) : null,
  })).filter((f: any) => f.year && f.rdPremium !== null)

  // Calculate summary stats
  const rdPremiumStats = publicationStats?.rd_factor_premium

  // Cumulative returns simulation
  const cumulativeData = premiumData.reduce((acc: any[], curr: any) => {
    const prev = acc[acc.length - 1]
    const q5Cumulative = prev ? prev.q5Cumulative * (1 + (curr.q5 || 0) / 100) : 1 + (curr.q5 || 0) / 100
    const q1Cumulative = prev ? prev.q1Cumulative * (1 + (curr.q1 || 0) / 100) : 1 + (curr.q1 || 0) / 100
    acc.push({
      year: curr.year,
      q5Cumulative,
      q1Cumulative,
      q5Return: (q5Cumulative - 1) * 100,
      q1Return: (q1Cumulative - 1) * 100,
    })
    return acc
  }, [] as Array<{ year: number; q5Cumulative: number; q1Cumulative: number; q5Return: number; q1Return: number }>)

  // Key metrics for the right sidebar
  const keyMetrics = [
    { label: "Mean Premium (annual)", value: rdPremiumStats?.mean !== undefined ? `${rdPremiumStats.mean.toFixed(1)}%` : "...", color: "text-purple-600 dark:text-purple-400" },
    { label: "t-Statistic", value: rdPremiumStats?.t_statistic !== undefined ? rdPremiumStats.t_statistic.toFixed(2) : "...", color: "text-blue-600 dark:text-blue-400" },
    { label: "Win Rate", value: rdPremiumStats ? `${Math.round((rdPremiumStats.positive_years / rdPremiumStats.n_years) * 100)}%` : "...", color: "text-green-600 dark:text-emerald-400" },
    { label: "Years Analyzed", value: `${premiumData.length}`, color: "text-foreground" },
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
        <Paper3FrontMatter
          premiumData={premiumData}
          rdPremiumStats={rdPremiumStats}
          handleDownload={handleDownload}
        />

        <Paper3Methods
          premiumData={premiumData}
          rdPremiumStats={rdPremiumStats}
        />

        {/* Results */}
        <section id="results" className="scroll-mt-24">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp className="h-5 w-5 text-primary" />
            <h2 className="text-2xl font-bold">5. Results</h2>
          </div>
          
          <div className="space-y-6">
            <Paper3ResultsCharts
              premiumData={premiumData}
              rdPremiumStats={rdPremiumStats}
              cumulativeData={cumulativeData}
            />

            <Paper3ResultsTables
              rdPremiumStats={rdPremiumStats}
              spanningTests={spanningTests}
              mispricingTests={mispricingTests}
              doubleSortData={doubleSortData}
            />
          </div>
        </section>

        <Paper3BackMatter
          rdPremiumStats={rdPremiumStats}
          premiumData={premiumData}
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

export default Paper3
