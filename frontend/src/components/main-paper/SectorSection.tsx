/** PATH: main-paper/SectorSection.tsx — Section 6: Sector Analysis (thin wrapper) */
import { Layers } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { SectorSectionCharts } from "./SectorSectionCharts"
import { SectorSectionTables } from "./SectorSectionTables"

export function SectorSection({ topSectors, sectorIntensityData, sectorCoverageData, sectorRadarData, rdTrendData, rdLeadersBySector }: { topSectors: any[]; sectorIntensityData: any[]; sectorCoverageData: any[]; sectorRadarData: any[]; rdTrendData: any[]; rdLeadersBySector: any[] }) {
  return (
    <section id="sector" className="scroll-mt-24 space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <Layers className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">6. Sector Analysis</h2>
      </div>

      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none">
          <p className="text-muted-foreground">
            <strong className="text-foreground">Why sector analysis matters:</strong> Sector composition is a key confounder for any R&amp;D-based sort.
            High-R&amp;D firms are concentrated in a small set of sectors (primarily Technology and Healthcare), and sector-wide shocks
            can mechanically influence the premium. If the R&amp;D premium is entirely driven by sector exposure, an investor could replicate
            it with a simpler sector bet.
          </p>
          <p className="text-muted-foreground mt-2">
            We therefore report (i) R&amp;D intensity by sector, (ii) coverage of eligible firms by sector for long-horizon windows, and
            (iii) descriptive sector trends and leaderboards. These exhibits are descriptive and are intended to support transparent
            interpretation of the return results. The key question is: <em>does the R&amp;D premium exist within sectors, or is it just a sector effect?</em>
          </p>
        </CardContent>
      </Card>

      <SectorSectionCharts topSectors={topSectors} sectorIntensityData={sectorIntensityData} sectorCoverageData={sectorCoverageData} sectorRadarData={sectorRadarData} />
      <SectorSectionTables rdTrendData={rdTrendData} rdLeadersBySector={rdLeadersBySector} />
    </section>
  )
}
