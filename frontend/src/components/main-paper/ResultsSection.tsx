/** PATH: main-paper/ResultsSection.tsx — Section 5: Results (thin wrapper) */
import { BarChart3 } from "lucide-react"
import { AnnualHMLTable } from "@/components/AnnualHMLTable"
import { InfoTooltip } from "@/components/InfoTooltip"
import { Card, CardContent } from "@/components/ui/card"
import { ResultsSectionCharts } from "./ResultsSectionCharts"
import { ResultsSectionTables } from "./ResultsSectionTables"

export function ResultsSection({ annualHmlData, snapshotLoading, quintileReturnBar5yr, rollingPremium5yr, headlinePremiums }: { annualHmlData: any; snapshotLoading: boolean; quintileReturnBar5yr: any[]; rollingPremium5yr: any[]; headlinePremiums: any[] }) {
  return (
    <section id="results" className="scroll-mt-24 space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <BarChart3 className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">5. Results</h2>
      </div>

      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none">
          <p className="text-muted-foreground">
            We report the main return evidence in three complementary views, each serving a distinct purpose:
          </p>
          <ul className="text-muted-foreground list-disc list-inside space-y-2 mt-2">
            <li>
              <strong className="text-foreground">Table 5.1 (Annual premium series):</strong> Non-overlapping annual observations{" "}
              <InfoTooltip term="non_overlapping" size={12} /> provide the cleanest basis for statistical inference.
              <em> This is our primary evidence.</em>
            </li>
            <li>
              <strong className="text-foreground">Figures 5.2-5.3 (Quintile returns and rolling premium):</strong> Visualize how returns differ across R&amp;D quintiles
              and how the premium evolves over time. These illustrate stability and regime dependence.
            </li>
            <li>
              <strong className="text-foreground">Table 5.4 (Horizon summaries):</strong> 5/10/20-year rolling windows{" "}
              <InfoTooltip term="rolling_window" size={12} /> as descriptive context.
              <em> Note: these are descriptive, not inferential, because windows overlap.</em>
            </li>
          </ul>
        </CardContent>
      </Card>

      <AnnualHMLTable
        data={annualHmlData}
        isLoading={snapshotLoading}
        title="5.1 Annual HML R&D Premium (Descriptive)"
        description="Non-overlapping annual observations (economic context; low power for inference)"
      />

      <ResultsSectionCharts quintileReturnBar5yr={quintileReturnBar5yr} rollingPremium5yr={rollingPremium5yr} />
      <ResultsSectionTables annualHmlData={annualHmlData} headlinePremiums={headlinePremiums} />
    </section>
  )
}
