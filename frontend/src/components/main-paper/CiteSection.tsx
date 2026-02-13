/**
 * PATH: frontend/src/components/main-paper/CiteSection.tsx
 * PURPOSE: "How to Cite" section with APA, BibTeX, and PDF links.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react: FileText, ExternalLink, Download icons
 *  - ui/button: copy-to-clipboard action
 */

import { FileText, ExternalLink, Download } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function CiteSection() {
  return (
    <section id="cite" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <FileText className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">How to Cite This Paper</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6 space-y-4">
          <div className="flex flex-wrap gap-3 mb-4">
            <a
              href="/rnd-alpha-paper.pdf"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              Open PDF
            </a>
            <a
              href="/rnd-alpha-paper.pdf"
              download
              className="inline-flex items-center px-4 py-2 border border-input bg-background rounded-md hover:bg-accent hover:text-accent-foreground transition-colors"
            >
              <Download className="mr-2 h-4 w-4" />
              Download PDF
            </a>
            <Button variant="outline" size="sm" onClick={() => {
              navigator.clipboard.writeText(
                `Sehgal, A. (2025). R&D Alpha: Investment Intensity and Long-Term Stock Returns (Working paper). FSE Research & Investments Pty Ltd. https://research.finsoeasy.com/rnd-alpha-paper.pdf`
              );
              alert("Citation copied to clipboard!");
            }}>
              Copy Citation
            </Button>
          </div>
          
          <div className="space-y-3">
            <div>
              <p className="text-sm font-semibold text-foreground mb-1">APA Format:</p>
              <p className="text-sm text-muted-foreground bg-muted p-3 rounded-md font-mono">
                Sehgal, A. (2025). R&amp;D Alpha: Investment Intensity and Long-Term Stock Returns (Working paper). <em>FSE Research &amp; Investments Pty Ltd</em>. https://research.finsoeasy.com/rnd-alpha-paper.pdf
              </p>
            </div>
            
            <div>
              <p className="text-sm font-semibold text-foreground mb-1">BibTeX:</p>
              <pre className="text-xs text-muted-foreground bg-muted p-3 rounded-md overflow-x-auto">
{`@techreport{sehgal_rnd_alpha_2025,
  author      = {Sehgal, Abhishek},
  title       = {R\\&D Alpha: Investment Intensity and Long-Term Stock Returns},
  institution = {FSE Research \\& Investments Pty Ltd},
  year        = {2025},
  month       = {12},
  url         = {https://research.finsoeasy.com/rnd-alpha-paper.pdf},
  note        = {Working paper; results pinned to a frozen publication snapshot (see PDF for snapshot ID).}
}`}
              </pre>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}
