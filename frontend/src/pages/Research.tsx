/**
 * PATH: src/pages/Research.tsx
 * PURPOSE: Research Analysis page — tabbed view of quintile, premium, ANOVA, cohort, papers, methodology
 * WHY: Parent orchestrator that wires the useResearchData hook to tab sub-components
 */

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useResearchData } from "@/hooks/useResearchData"
import {
  ResearchHeader,
  QuintileAnalysisTab,
  FactorPremiumTab,
  AnovaResultsTab,
  CompaniesTab,
  PapersTab,
  MethodologyTab,
  PnlEfficiencyTab,
} from "@/components/research"

export function Research() {
  const {
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
  } = useResearchData()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading research data...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <ResearchHeader
        selectedWindow={selectedWindow}
        setSelectedWindow={setSelectedWindow}
        cohortSummary={cohortSummary}
      />

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="flex flex-wrap h-auto gap-1 bg-muted/50 p-1">
          <TabsTrigger value="quintiles" className="flex-1 min-w-[120px]">Quintile Analysis</TabsTrigger>
          <TabsTrigger value="premium" className="flex-1 min-w-[120px]">Factor Premium</TabsTrigger>
          <TabsTrigger value="anova" className="flex-1 min-w-[120px]">ANOVA Results</TabsTrigger>
          <TabsTrigger value="companies" className="flex-1 min-w-[120px]">Cohort Companies</TabsTrigger>
          <TabsTrigger value="papers" className="flex-1 min-w-[80px]">Papers</TabsTrigger>
          <TabsTrigger value="methodology" className="flex-1 min-w-[100px]">Methodology</TabsTrigger>
          <TabsTrigger value="pnl-efficiency" className="flex-1 min-w-[120px]">PNL Efficiency</TabsTrigger>
        </TabsList>

        <TabsContent value="quintiles" className="space-y-4">
          <QuintileAnalysisTab
            selectedWindow={selectedWindow}
            chartsReady={chartsReady}
            quintilePerf={quintilePerf}
            rollingWindows={rollingWindows}
            handleExportQuintiles={handleExportQuintiles}
            formatPercent={formatPercent}
          />
        </TabsContent>

        <TabsContent value="premium" className="space-y-4">
          <FactorPremiumTab
            chartsReady={chartsReady}
            factorPremiums={factorPremiums}
          />
        </TabsContent>

        <TabsContent value="anova" className="space-y-4">
          <AnovaResultsTab
            aggregateAnova={aggregateAnova}
            formatPercent={formatPercent}
            formatPValue={formatPValue}
          />
        </TabsContent>

        <TabsContent value="companies" className="space-y-4">
          <CompaniesTab
            selectedWindow={selectedWindow}
            cohortCompanies={cohortCompanies}
            loadingCompanies={loadingCompanies}
            cohortSummary={cohortSummary}
            handleExportCohort={handleExportCohort}
          />
        </TabsContent>

        <TabsContent value="papers" className="space-y-4">
          <PapersTab />
        </TabsContent>

        <TabsContent value="methodology" className="space-y-4">
          <MethodologyTab />
        </TabsContent>

        <TabsContent value="pnl-efficiency" className="space-y-4">
          <PnlEfficiencyTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
