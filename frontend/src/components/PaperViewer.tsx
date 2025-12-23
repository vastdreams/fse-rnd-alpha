import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Download, FileText } from "lucide-react"

interface PaperViewerProps {
  title: string
  content: string
  onBack?: () => void
}

export function PaperViewer({ title, content, onBack }: PaperViewerProps) {
  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="text-2xl mb-2">{title}</CardTitle>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span>Research Paper</span>
            </div>
          </div>
          <div className="flex gap-2">
            {onBack && (
              <Button variant="outline" size="sm" onClick={onBack}>
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const blob = new Blob([content], { type: "text/markdown" })
                const url = URL.createObjectURL(blob)
                const a = document.createElement("a")
                a.href = url
                a.download = `${title.replace(/\s+/g, "_")}.md`
                a.click()
                URL.revokeObjectURL(url)
              }}
            >
              <Download className="h-4 w-4 mr-2" />
              Download
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="prose prose-invert prose-lg max-w-none dark:prose-invert">
          <div className="markdown-content bg-muted/30 p-6 rounded-lg overflow-auto max-h-[70vh] border">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ ...props }: any) => (
                  <h1 className="text-3xl font-bold mt-8 mb-4 text-foreground border-b border-border pb-2" {...props} />
                ),
                h2: ({ ...props }: any) => (
                  <h2 className="text-2xl font-semibold mt-6 mb-3 text-foreground" {...props} />
                ),
                h3: ({ ...props }: any) => (
                  <h3 className="text-xl font-semibold mt-4 mb-2 text-foreground" {...props} />
                ),
                h4: ({ ...props }: any) => (
                  <h4 className="text-lg font-medium mt-3 mb-2 text-foreground" {...props} />
                ),
                p: ({ ...props }: any) => (
                  <p className="mb-4 text-foreground leading-relaxed" {...props} />
                ),
                ul: ({ ...props }: any) => (
                  <ul className="list-disc list-inside mb-4 space-y-2 text-foreground ml-4" {...props} />
                ),
                ol: ({ ...props }: any) => (
                  <ol className="list-decimal list-inside mb-4 space-y-2 text-foreground ml-4" {...props} />
                ),
                li: ({ ...props }: any) => (
                  <li className="text-foreground" {...props} />
                ),
                strong: ({ ...props }: any) => (
                  <strong className="font-semibold text-foreground" {...props} />
                ),
                em: ({ ...props }: any) => (
                  <em className="italic text-foreground" {...props} />
                ),
                code: ({ inline, children, ...props }: any) => {
                  return inline ? (
                    <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground" {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className="block bg-muted p-4 rounded-lg text-sm font-mono text-foreground overflow-x-auto mb-4" {...props}>
                      {children}
                    </code>
                  )
                },
                blockquote: ({ ...props }: any) => (
                  <blockquote className="border-l-4 border-primary pl-4 italic my-4 text-muted-foreground" {...props} />
                ),
                table: ({ ...props }: any) => (
                  <div className="overflow-x-auto my-4">
                    <table className="min-w-full border-collapse border border-border" {...props} />
                  </div>
                ),
                thead: ({ ...props }: any) => (
                  <thead className="bg-muted" {...props} />
                ),
                th: ({ ...props }: any) => (
                  <th className="border border-border px-4 py-2 text-left font-semibold text-foreground" {...props} />
                ),
                td: ({ ...props }: any) => (
                  <td className="border border-border px-4 py-2 text-foreground" {...props} />
                ),
                a: ({ ...props }: any) => (
                  <a className="text-primary hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                ),
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

