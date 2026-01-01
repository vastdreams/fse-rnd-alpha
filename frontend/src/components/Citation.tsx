import { ExternalLink } from "lucide-react"
import references from "@/data/references.json"

interface Reference {
  id: string
  authors: string
  year: number
  title: string
  journal: string
  volume: string | null
  pages: string | null
  doi: string | null
  url?: string | null
  verified?: boolean
  peer_reviewed?: boolean
}

interface CitationProps {
  id: string
  inline?: boolean
}

export function Citation({ id, inline = true }: CitationProps) {
  const ref = (references as Record<string, Reference>)[id]
  
  if (!ref) {
    return <span className="text-red-400">[{id}?]</span>
  }

  if (inline) {
    // Render a citation-friendly author-year inline label:
    // - 1 author: "Fama, 1993"
    // - 2 authors: "Fama & French, 1993"
    // - 3+ authors: "Chan et al., 2001"
    // - Corporate author: "Financial Accounting Standards Board, 1974"
    const lastNames = Array.from(ref.authors.matchAll(/([A-Za-z][A-Za-z\-']+)\s*,/g)).map((m) => m[1])

    const inlineLabel =
      lastNames.length === 0
        ? `${ref.authors}, ${ref.year}`
        : lastNames.length === 1
          ? `${lastNames[0]}, ${ref.year}`
          : lastNames.length === 2
            ? `${lastNames[0]} & ${lastNames[1]}, ${ref.year}`
            : `${lastNames[0]} et al., ${ref.year}`

    return (
      <span 
        className="cursor-help text-primary hover:text-primary/80 font-medium"
        title={`${ref.title} - ${ref.authors} (${ref.year})`}
      >
        ({inlineLabel})
      </span>
    )
  }

  const linkUrl = ref.url || (ref.doi ? `https://doi.org/${ref.doi}` : null)

  return (
    <div className="text-sm text-muted-foreground">
      {ref.authors} ({ref.year}). {ref.title}. <em>{ref.journal}</em>{ref.volume && `, ${ref.volume}`}{ref.pages && `, ${ref.pages}`}.
      {linkUrl && (
        <a 
          href={linkUrl} 
          target="_blank" 
          rel="noopener noreferrer"
          className="text-blue-400 hover:underline ml-2 inline-flex items-center gap-1"
        >
          <ExternalLink className="h-3 w-3" />
          View
        </a>
      )}
    </div>
  )
}

interface ReferencesListProps {
  ids: string[]
}

export function ReferencesList({ ids }: ReferencesListProps) {
  const refs = ids
    .map(id => (references as Record<string, Reference>)[id])
    .filter(Boolean)
    .sort((a, b) => a.authors.localeCompare(b.authors))

  return (
    <div className="space-y-4">
      {refs.map((ref) => {
        const linkUrl = ref.url || (ref.doi ? `https://doi.org/${ref.doi}` : null)
        
        return (
          <div key={ref.id} className="p-3 rounded-lg bg-muted/30 border border-border/50 hover:border-border transition-colors">
            <p className="text-sm text-foreground">
              {ref.authors} ({ref.year}). {ref.title}. 
              <em className="text-muted-foreground"> {ref.journal}</em>
              {ref.volume && `, ${ref.volume}`}
              {ref.pages && `, ${ref.pages}`}.
            </p>
            {linkUrl && (
              <a 
                href={linkUrl} 
                target="_blank" 
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 mt-2 px-3 py-1.5 text-xs font-medium text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 rounded-md transition-colors"
              >
                <ExternalLink className="h-3 w-3" />
                Open Paper
              </a>
            )}
          </div>
        )
      })}
    </div>
  )
}

export function getAllReferenceIds(): string[] {
  return Object.keys(references)
}
