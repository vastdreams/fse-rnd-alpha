/**
 * PATH: frontend/src/pages/papers/MainPaper.tsx
 * PURPOSE:
 *   - Provide a single, publication-ready "Main Paper" page that consolidates the four sub-research pages
 *     (returns, sector patterns, factor tests, and fundamental discussion) into one cohesive narrative.
 *
 * ROLE IN ARCHITECTURE:
 *   - Frontend research communication layer (presentation + PDF/print export).
 *
 * MAIN EXPORTS:
 *   - MainPaper: the consolidated paper page component (practitioner-style on-site manuscript).
 *
 * NON-RESPONSIBILITIES:
 *   - This page does NOT compute research metrics (backend does).
 *   - This page does NOT store or mutate research results.
 *
 * NOTES:
 *   - No hard-coded numeric claims in prose. Any numeric claim must be sourced from:
 *     - live API responses, or
 *     - the frozen publication snapshot served by the backend.
 *   - Prefer rendering values dynamically from endpoints; avoid hard-coded result numbers in prose.
 *   - Keep "Sub-Research" pages as deep dives; the Main Paper should remain coherent and citable.
 *   - All section JSX has been extracted into components under @/components/main-paper/.
 */

import { useEffect, useState } from "react"
import { RightTableOfContents } from "@/components/RightTableOfContents"
import { useMainPaperData } from "@/hooks/useMainPaperData"
import { cn } from "@/lib/utils"

import {
  PaperHeader,
  ReaderGuide,
  AbstractSection,
  IntroductionSection,
  LiteratureSection,
  DataSection,
  MethodologySection,
  ResultsSection,
  SectorSection,
  RobustnessSection,
  DiscussionSection,
  StrategySection,
  LimitationsSection,
  ReplicabilitySection,
  ConclusionSection,
  CiteSection,
  ReferencesSection,
  AppendixSection,
} from "@/components/main-paper"

// Table of contents sections
const sections = [
  { id: "abstract", label: "Abstract" },
  { id: "introduction", label: "1. Introduction" },
  { id: "literature", label: "2. Literature Review & Hypotheses" },
  { id: "data", label: "3. Data & Sample Construction" },
  { id: "methodology", label: "4. Methodology" },
  { id: "results", label: "5. Results" },
  { id: "sector", label: "6. Sector Analysis" },
  { id: "robustness", label: "7. Robustness & Factor Tests" },
  { id: "discussion", label: "8. Discussion" },
  { id: "strategy", label: "9. Investable Strategy" },
  { id: "limitations", label: "10. Limitations" },
  { id: "replicability", label: "11. Replicability" },
  { id: "conclusion", label: "12. Conclusion" },
  { id: "cite", label: "How to Cite" },
  { id: "references", label: "References" },
  { id: "appendix", label: "Online Appendix (Supporting Notes)" },
]

export function MainPaper() {
  const [activeSection, setActiveSection] = useState("abstract")
  const [rightNavCollapsed, setRightNavCollapsed] = useState(false)

  // All data computation extracted to useMainPaperData hook
  const {
    snapshot,
    snapshotLoading,
    snapshotPayload,
    cohortSummary,
    annualHmlData,
    netOfCost5yr,
    rollingAggregates,
    transactionCosts,
    methodologyParameters,
    publicationStats,
    spanningTests,
    ff5AlphaPercent,
    ff5AlphaPValue,
    mispricingTests,
    investableBacktest,
    delistingSensitivity,
    topSectors,
    headlinePremiums,
    quintileReturnBar5yr,
    rollingPremium5yr,
    rolling20yrEndpoints,
    sectorIntensityData,
    sectorCoverageData,
    sectorRadarData,
    rdTrendData,
    rdLeadersBySector,
    doubleSortTableRows,
    factorPremiumSeries,
    regimePremiumTable,
    sampleYearRange,
    snapshotBuiltAtLabel,
    returnConventionLabel,
    growthOf1,
    investableGrowth,
    investableNetExcessVsSp500Pp,
    investableTurnoverAvgPct,
    investableUnderperformPct,
  } = useMainPaperData()

  const handleDownloadPDF = () => {
    window.open("/rnd-alpha-paper.pdf", "_blank", "noopener,noreferrer")
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) setActiveSection(entry.target.id)
        })
      },
      { rootMargin: "-20% 0px -60% 0px" }
    )

    sections.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    return () => observer.disconnect()
  }, [])

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  return (
    <div className="flex justify-center min-h-0">
      <div className="flex w-full max-w-screen-2xl gap-8">
        <div
          className={cn(
            "flex-1 min-w-0 space-y-12 pb-24 transition-all duration-300 print-content",
            rightNavCollapsed ? "max-w-none" : "max-w-4xl mx-auto"
          )}
        >
        {/* Header */}
        <PaperHeader
          cohortSummary={cohortSummary}
          sampleYearRange={sampleYearRange}
          returnConventionLabel={returnConventionLabel}
          snapshotBuiltAtLabel={snapshotBuiltAtLabel}
          onDownloadPDF={handleDownloadPDF}
        />

        {/* Reader Guide */}
        <ReaderGuide />

        {/* Abstract */}
        <AbstractSection
          cohortSummary={cohortSummary}
          sampleYearRange={sampleYearRange}
          annualHmlData={annualHmlData}
          ff5AlphaPercent={ff5AlphaPercent}
          ff5AlphaPValue={ff5AlphaPValue}
          transactionCosts={transactionCosts}
        />

        {/* 1. Introduction */}
        <IntroductionSection />

        {/* 2. Literature Review & Hypotheses */}
        <LiteratureSection />

        {/* 3. Data & Sample Construction */}
        <DataSection sampleYearRange={sampleYearRange} />

        {/* 4. Methodology */}
        <MethodologySection
          methodologyParameters={methodologyParameters}
          snapshot={snapshot}
        />

        {/* 5. Results */}
        <ResultsSection
          annualHmlData={annualHmlData}
          snapshotLoading={snapshotLoading}
          quintileReturnBar5yr={quintileReturnBar5yr}
          rollingPremium5yr={rollingPremium5yr}
          headlinePremiums={headlinePremiums}
        />

        {/* 6. Sector Analysis */}
        <SectorSection
          topSectors={topSectors}
          sectorIntensityData={sectorIntensityData}
          sectorCoverageData={sectorCoverageData}
          sectorRadarData={sectorRadarData}
          rdTrendData={rdTrendData}
          rdLeadersBySector={rdLeadersBySector}
        />

        {/* 7. Robustness & Factor Tests */}
        <RobustnessSection
          publicationStats={publicationStats}
          factorPremiumSeries={factorPremiumSeries}
          growthOf1={growthOf1}
          spanningTests={spanningTests}
          annualHmlData={annualHmlData}
          snapshotPayload={snapshotPayload}
          mispricingTests={mispricingTests}
          doubleSortTableRows={doubleSortTableRows}
          delistingSensitivity={delistingSensitivity}
        />

        {/* 8. Discussion */}
        <DiscussionSection
          snapshotPayload={snapshotPayload}
          annualHmlData={annualHmlData}
          headlinePremiums={headlinePremiums}
          transactionCosts={transactionCosts}
          rolling20yrEndpoints={rolling20yrEndpoints}
          regimePremiumTable={regimePremiumTable}
        />

        {/* 9. Investable Strategy */}
        <StrategySection
          transactionCosts={transactionCosts}
          netOfCost5yr={netOfCost5yr}
          rollingAggregates={rollingAggregates}
          investableBacktest={investableBacktest}
          investableGrowth={investableGrowth}
          cohortSummary={cohortSummary}
          investableNetExcessVsSp500Pp={investableNetExcessVsSp500Pp}
          investableUnderperformPct={investableUnderperformPct}
          investableTurnoverAvgPct={investableTurnoverAvgPct}
        />

        {/* 10. Limitations */}
        <LimitationsSection />

        {/* 11. Replicability */}
        <ReplicabilitySection
          snapshot={snapshot}
          snapshotBuiltAtLabel={snapshotBuiltAtLabel}
        />

        {/* 12. Conclusion */}
        <ConclusionSection
          annualHmlData={annualHmlData}
          headlinePremiums={headlinePremiums}
          netOfCost5yr={netOfCost5yr}
          transactionCosts={transactionCosts}
        />

        {/* How to Cite */}
        <CiteSection />

        {/* References */}
        <ReferencesSection />

        {/* Online Appendix */}
        <AppendixSection />
      </div>

        {/* Right navigation */}
        <RightTableOfContents
          sections={sections}
          activeSection={activeSection}
          onSectionClick={scrollToSection}
          keyMetrics={[]}
          onCollapseChange={setRightNavCollapsed}
        />
      </div>
    </div>
  )
}
