/**
 * PATH: frontend/src/pages/Methodology.tsx
 * PURPOSE: Standalone methodology page — composes sub-components for each content group
 * WHY: Parent orchestrator; keeps per-file line count under 300
 * FLOW:
 * ┌────────────────────┐   ┌─────────────────────────┐   ┌──────────────────────┐
 * │ publicationSnapshot │ → │ keyMetrics / labels      │ → │ Header + Sub-comps   │
 * └────────────────────┘   └─────────────────────────┘   └──────────────────────┘
 * DEPENDENCIES:
 *   - methodology/*: section sub-components
 *   - RightTableOfContents: sidebar navigation
 *   - @tanstack/react-query: snapshot data fetching
 */

import { useState, useEffect, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { Badge } from "@/components/ui/badge"
import { Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import {
  MethodologyDataSources,
  MethodologyAnalysis,
  MethodologyCaveats,
  MethodologyReplication,
} from "@/components/methodology"

const sections = [
  { id: "overview", label: "Overview" },
  { id: "data-sources", label: "1. Data Sources" },
  { id: "rd-intensity", label: "2. R&D Intensity" },
  { id: "quintile-construction", label: "3. Quintile Construction" },
  { id: "return-calculation", label: "4. Return Calculation" },
  { id: "statistical-tests", label: "5. Statistical Tests" },
  { id: "fiscal-year-handling", label: "6. Fiscal Year Handling" },
  { id: "sector-bias", label: "7. Sector Bias" },
  { id: "limitations", label: "8. Limitations" },
  { id: "replication", label: "9. Replication Guide" },
  { id: "verification", label: "10. Verification Checklist" },
]

export function Methodology() {
  const [activeSection, setActiveSection] = useState("overview")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // "0 hallucinations" policy: any displayed counts/ranges should come from snapshot-backed API.
  const { data: publicationSnapshot } = useQuery({
    queryKey: ["publicationSnapshot", "methodology"],
    queryFn: () => api.getPublicationSnapshot(),
  })

  const companiesLabel = useMemo(() => {
    const cohort = publicationSnapshot?.payload?.cohort_summary as any
    const totalCompanies = cohort && typeof cohort === "object" && !("error" in cohort) ? cohort.total_companies : undefined
    return typeof totalCompanies === "number" ? String(totalCompanies) : "..."
  }, [publicationSnapshot])

  const timePeriodLabel = useMemo(() => {
    const annual = publicationSnapshot?.payload?.annual_hml_premium as any
    if (!annual || typeof annual !== "object" || ("error" in annual)) return "..."
    const rows = annual.annual_premiums
    const nYears = annual.n_years
    if (!Array.isArray(rows) || rows.length === 0) return "..."
    const first = rows[0]?.year
    const last = rows[rows.length - 1]?.year
    if (typeof first !== "string" || typeof last !== "string") return "..."
    const range = `${first} to ${last}`
    return typeof nYears === "number" ? `${range} (${nYears} yrs)` : range
  }, [publicationSnapshot])

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

  const keyMetrics = [
    { label: "Data Sources", value: "3", color: "text-blue-500" },
    { label: "Companies", value: companiesLabel, color: "text-emerald-500" },
    { label: "Time Period", value: timePeriodLabel, color: "text-purple-500" },
    { label: "Quintiles", value: "5", color: "text-foreground" },
  ]

  return (
    <div className="flex gap-8">
      {/* Main Content */}
      <div className={cn(
        "flex-1 space-y-12 pb-24 transition-all duration-300",
        rightNavCollapsed ? "max-w-none" : "max-w-4xl"
      )}>
        {/* Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-card to-card border border-blue-500/20 p-8">
          <div className="absolute inset-0 bg-grid-white/[0.02] dark:bg-grid-white/[0.02]" />
          <div className="relative z-10">
            <div className="flex items-start justify-between flex-wrap gap-4 mb-6">
              <Badge variant="outline" className="text-blue-500 border-blue-500/30">
                Methodology Documentation
              </Badge>
              <Button variant="outline" size="sm" asChild>
                <a href="/rnd-alpha-paper.pdf" target="_blank" rel="noopener noreferrer">
                <Download className="mr-2 h-4 w-4" />
                Download PDF
                </a>
              </Button>
            </div>
            
            <h1 className="text-4xl font-bold mb-4">
              <span className="text-blue-500">Research</span>{" "}
              <span className="text-foreground">Methodology</span>
            </h1>
            <p className="text-xl text-muted-foreground max-w-3xl">
              First-Principles Documentation of R&D Factor Analysis
            </p>
            
            <div className="flex flex-wrap gap-6 mt-6 pt-6 border-t border-border text-sm">
              <div><span className="text-muted-foreground">Version:</span> <span className="text-foreground">2.0</span></div>
              <div><span className="text-muted-foreground">Last Updated:</span> <span className="text-foreground">January 2026</span></div>
              <div><span className="text-muted-foreground">Author:</span> <span className="text-foreground">Abhishek Sehgal</span></div>
            </div>
          </div>
        </div>

        {/* Section groups — each sub-component renders its own <section> elements */}
        <MethodologyDataSources />
        <MethodologyAnalysis />
        <MethodologyCaveats />
        <MethodologyReplication />
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
