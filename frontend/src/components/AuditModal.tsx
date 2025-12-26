/**
 * PATH: frontend/src/components/AuditModal.tsx
 * PURPOSE: Data Audit Modal - Chain of Thought breakdown with AI analysis
 * 
 * Shows the source logic and computation steps for any metric,
 * allowing users to verify and understand how numbers are calculated.
 */

import { useState } from "react"
import { X, Copy, Check, Database, Sparkles, ChevronDown, ChevronUp, ExternalLink } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

export interface AuditStep {
  stepNumber: number
  type: "source" | "computation" | "filter" | "aggregation" | "formula" | "info"
  title: string
  description: string
  sources?: {
    label: string
    value: string
    link?: string
  }[]
  formula?: string
  note?: string
}

export interface AuditData {
  metricId: string
  metricName: string
  value: string
  period?: string
  status?: "verified" | "warning" | "info"
  statusText?: string
  steps: AuditStep[]
  aiAnalysis?: string
  lastUpdated?: string
}

interface AuditModalProps {
  isOpen: boolean
  onClose: () => void
  data: AuditData | null
}

const stepTypeColors: Record<AuditStep["type"], string> = {
  source: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  computation: "bg-purple-500/10 border-purple-500/30 text-purple-400",
  filter: "bg-amber-500/10 border-amber-500/30 text-amber-400",
  aggregation: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
  formula: "bg-pink-500/10 border-pink-500/30 text-pink-400",
  info: "bg-slate-500/10 border-slate-500/30 text-slate-400",
}

export function AuditModal({ isOpen, onClose, data }: AuditModalProps) {
  const [activeTab, setActiveTab] = useState<"trace" | "analysis">("trace")
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set([1]))
  const [copied, setCopied] = useState(false)

  if (!isOpen || !data) return null

  const handleCopy = async () => {
    const text = `${data.metricName}: ${data.value}`
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const toggleStep = (stepNumber: number) => {
    const newExpanded = new Set(expandedSteps)
    if (newExpanded.has(stepNumber)) {
      newExpanded.delete(stepNumber)
    } else {
      newExpanded.add(stepNumber)
    }
    setExpandedSteps(newExpanded)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-card border border-border rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center">
              <Database className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-foreground">Data Audit</h2>
              <p className="text-sm text-muted-foreground">Chain of Thought breakdown with AI analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="text-muted-foreground hover:text-foreground"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span className="ml-1">{copied ? "Copied" : "Copy"}</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Metric Summary */}
        <div className="p-6 bg-muted/30 border-b border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted-foreground uppercase tracking-wide">METRIC</p>
              <p className="text-lg font-medium text-foreground">{data.metricName}</p>
              {data.period && (
                <p className="text-sm text-muted-foreground">Period: {data.period}</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs text-muted-foreground uppercase tracking-wide">VALUE</p>
              <p className={cn(
                "text-2xl font-bold",
                data.value.startsWith("+") ? "text-emerald-500" : 
                data.value.startsWith("-") ? "text-red-500" : "text-foreground"
              )}>
                {data.value}
              </p>
              {data.status && (
                <p className={cn(
                  "text-sm flex items-center justify-end gap-1",
                  data.status === "verified" ? "text-emerald-500" :
                  data.status === "warning" ? "text-amber-500" : "text-muted-foreground"
                )}>
                  {data.status === "warning" && "⚠️"}
                  {data.status === "verified" && "✓"}
                  {data.statusText}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-border">
          <button
            onClick={() => setActiveTab("trace")}
            className={cn(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2",
              activeTab === "trace"
                ? "text-foreground border-b-2 border-primary bg-muted/30"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Database className="w-4 h-4" />
            Data Trace
          </button>
          <button
            onClick={() => setActiveTab("analysis")}
            className={cn(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2",
              activeTab === "analysis"
                ? "text-foreground border-b-2 border-primary bg-muted/30"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <Sparkles className="w-4 h-4" />
            AI Analysis
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === "trace" ? (
            <div className="space-y-4">
              {data.steps.map((step, index) => (
                <div 
                  key={step.stepNumber}
                  className={cn(
                    "rounded-lg border transition-all",
                    expandedSteps.has(step.stepNumber) 
                      ? "bg-card" 
                      : "bg-muted/20"
                  )}
                >
                  {/* Step Header */}
                  <button
                    onClick={() => toggleStep(step.stepNumber)}
                    className="w-full px-4 py-3 flex items-start gap-3 text-left"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-muted/50 border border-border flex items-center justify-center shrink-0">
                        <Database className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-muted-foreground">
                            STEP {step.stepNumber}
                          </span>
                          <span className={cn(
                            "text-xs px-2 py-0.5 rounded-full border",
                            stepTypeColors[step.type]
                          )}>
                            {step.type}
                          </span>
                        </div>
                        <p className="font-medium text-foreground">{step.title}</p>
                        <p className="text-sm text-muted-foreground line-clamp-1">
                          {step.description}
                        </p>
                      </div>
                    </div>
                    {expandedSteps.has(step.stepNumber) ? (
                      <ChevronUp className="w-5 h-5 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-muted-foreground shrink-0" />
                    )}
                  </button>

                  {/* Step Details */}
                  {expandedSteps.has(step.stepNumber) && (
                    <div className="px-4 pb-4 pt-0 space-y-3">
                      {/* Sources */}
                      {step.sources && step.sources.length > 0 && (
                        <div className="bg-muted/30 rounded-lg p-3 space-y-2">
                          <p className="text-xs font-medium text-muted-foreground flex items-center gap-1">
                            📁 {step.sources.length} source{step.sources.length > 1 ? "s" : ""}
                          </p>
                          <ul className="space-y-1.5 text-sm">
                            {step.sources.map((source, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-muted-foreground">•</span>
                                <span className="text-muted-foreground">{source.label}:</span>
                                <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono text-foreground">
                                  {source.value}
                                </code>
                                {source.link && (
                                  <a 
                                    href={source.link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-primary hover:underline"
                                  >
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Formula */}
                      {step.formula && (
                        <div className="bg-purple-500/5 border border-purple-500/20 rounded-lg p-3">
                          <p className="text-xs font-medium text-purple-400 mb-1">Formula</p>
                          <code className="text-sm font-mono text-foreground block whitespace-pre-wrap">
                            {step.formula}
                          </code>
                        </div>
                      )}

                      {/* Note */}
                      {step.note && (
                        <p className="text-sm text-muted-foreground italic">
                          💡 {step.note}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Connector Line */}
                  {index < data.steps.length - 1 && (
                    <div className="flex justify-center -mb-2">
                      <div className="w-px h-4 bg-border" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {data.aiAnalysis ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <div className="bg-gradient-to-br from-purple-500/5 to-pink-500/5 border border-purple-500/20 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-5 h-5 text-purple-400" />
                      <span className="font-medium text-foreground">AI Analysis</span>
                    </div>
                    <div className="text-sm text-muted-foreground whitespace-pre-wrap">
                      {data.aiAnalysis}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>AI analysis not available for this metric</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-muted/20 flex items-center justify-between text-xs text-muted-foreground">
          <span>{data.steps.length} steps in trace</span>
          {data.lastUpdated && (
            <span>Last updated: {data.lastUpdated}</span>
          )}
        </div>
      </div>
    </div>
  )
}

// Context Menu Component
interface AuditContextMenuProps {
  x: number
  y: number
  onClose: () => void
  onAudit: () => void
  onCopyValue: () => void
  onCopyWithLabel: () => void
  metricName: string
  value: string
}

export function AuditContextMenu({
  x,
  y,
  onClose,
  onAudit,
  onCopyValue,
  onCopyWithLabel,
  // metricName and value are passed for potential future use (e.g., showing in menu)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  metricName: _metricName,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  value: _value,
}: AuditContextMenuProps) {
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-40"
        onClick={onClose}
      />
      
      {/* Menu */}
      <div 
        className="fixed z-50 bg-card border border-border rounded-lg shadow-xl py-1 min-w-[200px]"
        style={{ left: x, top: y }}
      >
        <button
          onClick={() => { onAudit(); onClose(); }}
          className="w-full px-4 py-2.5 text-left text-sm hover:bg-muted flex items-center gap-3 group"
        >
          <Database className="w-4 h-4 text-muted-foreground group-hover:text-primary" />
          <div>
            <span className="text-foreground">Audit Data Point</span>
            <span className="text-xs text-muted-foreground ml-2">Chain of Thought</span>
          </div>
        </button>
        
        <div className="h-px bg-border my-1" />
        
        <button
          onClick={() => { onCopyValue(); onClose(); }}
          className="w-full px-4 py-2 text-left text-sm hover:bg-muted flex items-center gap-3"
        >
          <Copy className="w-4 h-4 text-muted-foreground" />
          <span className="text-foreground">Copy Value</span>
        </button>
        
        <button
          onClick={() => { onCopyWithLabel(); onClose(); }}
          className="w-full px-4 py-2 text-left text-sm hover:bg-muted flex items-center gap-3"
        >
          <Copy className="w-4 h-4 text-muted-foreground" />
          <span className="text-foreground">Copy with Label</span>
        </button>
        
        <div className="h-px bg-border my-1" />
        
        <div className="px-4 py-2 text-xs text-muted-foreground">
          <span className="opacity-60">View Source Documents</span>
          <span className="ml-2 text-xs opacity-40">Soon</span>
        </div>
        <div className="px-4 py-2 text-xs text-muted-foreground">
          <span className="opacity-60">Export to Report</span>
          <span className="ml-2 text-xs opacity-40">Soon</span>
        </div>
      </div>
    </>
  )
}

