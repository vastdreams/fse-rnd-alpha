/**
 * PATH: frontend/src/components/main-paper/AppendixSection.tsx
 * PURPOSE: Online Appendix section with links to Sub-Research pages.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - react-router-dom Link: internal navigation to sub-research pages
 *  - lucide-react Layers: section icon
 *  - ui/card: Card + CardHeader + CardContent + CardTitle + CardDescription
 */

import { Link } from "react-router-dom"
import { Layers } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export function AppendixSection() {
  return (
    <section id="appendix" className="scroll-mt-24 space-y-6">
      <div className="flex items-center gap-3 mb-4">
        <Layers className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">Online Appendix (Supporting Notes)</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 prose dark:prose-invert max-w-none space-y-3">
          <p className="text-muted-foreground">
            The Main Paper is designed to be self-contained. The pages below are supporting notes that provide additional
            narrative detail and exploratory visuals. All headline numbers in the Main Paper are sourced from the frozen
            publication snapshot.
          </p>
          <p className="text-muted-foreground">
            If you are reviewing this manuscript, you can treat the supporting notes as an online appendix rather than required reading.
          </p>
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-2 gap-4">
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Sub-Research 1</CardTitle>
            <CardDescription>Core returns + inference visuals</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/papers/1" className="underline hover:no-underline text-primary">
              Open Sub-Research 1
            </Link>
          </CardContent>
        </Card>
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Sub-Research 2</CardTitle>
            <CardDescription>Sector patterns + data coverage</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/papers/2" className="underline hover:no-underline text-primary">
              Open Sub-Research 2
            </Link>
          </CardContent>
        </Card>
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Sub-Research 3</CardTitle>
            <CardDescription>Factor tests + robustness suite</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/papers/3" className="underline hover:no-underline text-primary">
              Open Sub-Research 3
            </Link>
          </CardContent>
        </Card>
        <Card className="bg-card">
          <CardHeader>
            <CardTitle>Sub-Research 4</CardTitle>
            <CardDescription>Mechanisms (qualitative) + interpretation</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/papers/4" className="underline hover:no-underline text-primary">
              Open Sub-Research 4
            </Link>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}
