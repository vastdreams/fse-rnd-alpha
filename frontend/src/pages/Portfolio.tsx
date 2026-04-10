/**
 * PATH: frontend/src/pages/Portfolio.tsx
 * PURPOSE: Interactive "ETF{N} R&D Alpha Selection" page – holdings, performance, sector allocation, methodology.
 * WHY: Provides a portfolio/implementation view of the R&D Alpha research.
 * FLOW:
 *   usePortfolioData(state) → data → sub-components render tabs + charts
 */
import { useState, useEffect } from "react"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FlaskConical, Scale } from "lucide-react"
import type { AlphaFamily } from "@/lib/api/types"
import { usePortfolioData } from "@/hooks/usePortfolioData"
import {
  PortfolioHeader,
  PortfolioInfo,
  PortfolioChart,
  PortfolioSummary,
  PortfolioCoreTabs,
  PortfolioMethodologyTab,
  PortfolioSectorWeightsTab,
} from "@/components/portfolio"

export function Portfolio() {
  const [asOfYear, setAsOfYear] = useState(2023)
  const [nHoldings, setNHoldings] = useState(20)
  const [selectedSector, setSelectedSector] = useState<string | undefined>()
  const [chartsReady, setChartsReady] = useState(false)
  const [activeTab, setActiveTab] = useState("holdings")
  const [alphaFamily, setAlphaFamily] = useState<AlphaFamily>("rd_alpha")
  const [showMethodologyDetails, setShowMethodologyDetails] = useState(false)

  // Delay chart rendering to ensure container dimensions are calculated
  useEffect(() => {
    setChartsReady(false)
    const rafId = requestAnimationFrame(() => {
      const timer = setTimeout(() => setChartsReady(true), 250)
      return () => clearTimeout(timer)
    })
    return () => cancelAnimationFrame(rafId)
  }, [activeTab])

  const data = usePortfolioData(asOfYear, nHoldings, selectedSector, alphaFamily)

  if (data.isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-4 border-primary border-t-transparent animate-spin" />
          <div className="text-lg text-muted-foreground">Building your R&D Alpha portfolio...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Alpha Family Toggle */}
      <div className="flex items-center gap-3 mb-2">
        <span className="text-sm font-medium text-muted-foreground">Alpha:</span>
        <div className="flex rounded-lg border border-border overflow-hidden">
          <button
            className={`px-4 py-1.5 text-sm font-medium transition-colors ${alphaFamily === "rd_alpha" ? "bg-primary text-primary-foreground" : "bg-muted/50 hover:bg-muted"}`}
            onClick={() => setAlphaFamily("rd_alpha")}
          >
            R&D Alpha
          </button>
          <button
            className={`px-4 py-1.5 text-sm font-medium transition-colors ${alphaFamily === "pnl_efficiency" ? "bg-primary text-primary-foreground" : "bg-muted/50 hover:bg-muted"}`}
            onClick={() => setAlphaFamily("pnl_efficiency")}
          >
            PNL Efficiency
          </button>
        </div>
      </div>

      <PortfolioHeader
        data={data}
        asOfYear={asOfYear} setAsOfYear={setAsOfYear}
        nHoldings={nHoldings} setNHoldings={setNHoldings}
        selectedSector={selectedSector} setSelectedSector={setSelectedSector}
      />

      <PortfolioInfo data={data} asOfYear={asOfYear} nHoldings={nHoldings} />

      <PortfolioChart data={data} nHoldings={nHoldings} asOfYear={asOfYear} chartsReady={chartsReady} />

      <PortfolioSummary data={data} nHoldings={nHoldings} />

      <Tabs defaultValue="holdings" value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="bg-muted/50 flex-wrap">
          <TabsTrigger value="holdings">Holdings ({asOfYear})</TabsTrigger>
          <TabsTrigger value="performance">Performance History</TabsTrigger>
          <TabsTrigger value="allocation">Sector Allocation</TabsTrigger>
          <TabsTrigger value="methodology"><FlaskConical className="w-4 h-4 mr-1" />Methodology</TabsTrigger>
          <TabsTrigger value="sector-weights"><Scale className="w-4 h-4 mr-1" />Sector Weights</TabsTrigger>
        </TabsList>

        <PortfolioCoreTabs data={data} asOfYear={asOfYear} nHoldings={nHoldings} chartsReady={chartsReady} activeTab={activeTab} />
        <PortfolioMethodologyTab data={data} showMethodologyDetails={showMethodologyDetails} setShowMethodologyDetails={setShowMethodologyDetails} />
        <PortfolioSectorWeightsTab data={data} nHoldings={nHoldings} asOfYear={asOfYear} />
      </Tabs>
    </div>
  )
}

export default Portfolio
