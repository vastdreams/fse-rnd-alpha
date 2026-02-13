/** PATH: main-paper/DiscussionSection.tsx — Section 8: Discussion (thin wrapper) */
import { BookOpen } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { DiscussionSectionEvidence } from "./DiscussionSectionEvidence"
import { DiscussionSectionAnalysis } from "./DiscussionSectionAnalysis"

export function DiscussionSection({ snapshotPayload, annualHmlData, headlinePremiums, transactionCosts, rolling20yrEndpoints, regimePremiumTable }: { snapshotPayload: any; annualHmlData: any; headlinePremiums: any[]; transactionCosts: any; rolling20yrEndpoints: any; regimePremiumTable: any[] }) {
  return (
    <section id="discussion" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <BookOpen className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">8. Discussion</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-6">
          <DiscussionSectionEvidence
            snapshotPayload={snapshotPayload}
            annualHmlData={annualHmlData}
            headlinePremiums={headlinePremiums}
            transactionCosts={transactionCosts}
            rolling20yrEndpoints={rolling20yrEndpoints}
            regimePremiumTable={regimePremiumTable}
          />
          <DiscussionSectionAnalysis />
        </CardContent>
      </Card>
    </section>
  )
}
