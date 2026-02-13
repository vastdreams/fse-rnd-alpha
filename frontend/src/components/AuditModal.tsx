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
import { stepTypeColors } from "./AuditModalContent"
import type { AuditData } from "./AuditModalContent"

// Re-export types and components so existing consumers keep working
export type { AuditStep, AuditData } from "./AuditModalContent"
export { AuditContextMenu } from "./AuditModalContent"

interface AuditModalProps {
  isOpen: boolean
  onClose: () => void
  data: AuditData | null
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
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal - solid white background for readability */}
      <div className="relative bg-white border border-gray-200 rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center">
              <Database className="w-6 h-6 text-emerald-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Data Audit</h2>
              <p className="text-sm text-gray-500">Chain of Thought breakdown with AI analysis</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              className="text-gray-500 hover:text-gray-900 hover:bg-gray-100"
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span className="ml-1">{copied ? "Copied" : "Copy"}</span>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-gray-500 hover:text-gray-900 hover:bg-gray-100"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Metric Summary */}
        <div className="p-6 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide">METRIC</p>
              <p className="text-lg font-medium text-gray-900">{data.metricName}</p>
              {data.period && (
                <p className="text-sm text-gray-500">Period: {data.period}</p>
              )}
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500 uppercase tracking-wide">VALUE</p>
              <p className={cn(
                "text-2xl font-bold",
                data.value.startsWith("+") ? "text-emerald-600" : 
                data.value.startsWith("-") ? "text-red-600" : "text-gray-900"
              )}>
                {data.value}
              </p>
              {data.status && (
                <p className={cn(
                  "text-sm flex items-center justify-end gap-1",
                  data.status === "verified" ? "text-emerald-600" :
                  data.status === "warning" ? "text-amber-600" : "text-gray-500"
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
        <div className="flex border-b border-gray-200 bg-white">
          <button
            onClick={() => setActiveTab("trace")}
            className={cn(
              "flex-1 px-4 py-3 text-sm font-medium transition-colors flex items-center justify-center gap-2",
              activeTab === "trace"
                ? "text-gray-900 border-b-2 border-emerald-600 bg-gray-50"
                : "text-gray-500 hover:text-gray-900"
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
                ? "text-gray-900 border-b-2 border-emerald-600 bg-gray-50"
                : "text-gray-500 hover:text-gray-900"
            )}
          >
            <Sparkles className="w-4 h-4" />
            AI Analysis
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-white">
          {activeTab === "trace" ? (
            <div className="space-y-4">
              {data.steps.map((step, index) => (
                <div 
                  key={step.stepNumber}
                  className={cn(
                    "rounded-lg border border-gray-200 transition-all",
                    expandedSteps.has(step.stepNumber) 
                      ? "bg-white" 
                      : "bg-gray-50"
                  )}
                >
                  {/* Step Header */}
                  <button
                    onClick={() => toggleStep(step.stepNumber)}
                    className="w-full px-4 py-3 flex items-start gap-3 text-left"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="w-10 h-10 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center shrink-0">
                        <Database className="w-5 h-5 text-gray-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-gray-500">
                            STEP {step.stepNumber}
                          </span>
                          <span className={cn(
                            "text-xs px-2 py-0.5 rounded-full border",
                            stepTypeColors[step.type]
                          )}>
                            {step.type}
                          </span>
                        </div>
                        <p className="font-medium text-gray-900">{step.title}</p>
                        <p className="text-sm text-gray-500 line-clamp-1">
                          {step.description}
                        </p>
                      </div>
                    </div>
                    {expandedSteps.has(step.stepNumber) ? (
                      <ChevronUp className="w-5 h-5 text-gray-400 shrink-0" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-gray-400 shrink-0" />
                    )}
                  </button>

                  {/* Step Details */}
                  {expandedSteps.has(step.stepNumber) && (
                    <div className="px-4 pb-4 pt-0 space-y-3">
                      {/* Sources */}
                      {step.sources && step.sources.length > 0 && (
                        <div className="bg-gray-50 rounded-lg p-3 space-y-2">
                          <p className="text-xs font-medium text-gray-500 flex items-center gap-1">
                            📁 {step.sources.length} source{step.sources.length > 1 ? "s" : ""}
                          </p>
                          <ul className="space-y-1.5 text-sm">
                            {step.sources.map((source, i) => (
                              <li key={i} className="flex items-start gap-2">
                                <span className="text-gray-400">•</span>
                                <span className="text-gray-600">{source.label}:</span>
                                <code className="text-xs bg-gray-100 px-1.5 py-0.5 rounded font-mono text-gray-900">
                                  {source.value}
                                </code>
                                {source.link && (
                                  <a 
                                    href={source.link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-emerald-600 hover:underline"
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
                        <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                          <p className="text-xs font-medium text-purple-600 mb-1">Formula</p>
                          <code className="text-sm font-mono text-gray-900 block whitespace-pre-wrap">
                            {step.formula}
                          </code>
                        </div>
                      )}

                      {/* Note */}
                      {step.note && (
                        <p className="text-sm text-gray-500 italic">
                          💡 {step.note}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Connector Line */}
                  {index < data.steps.length - 1 && (
                    <div className="flex justify-center -mb-2">
                      <div className="w-px h-4 bg-gray-200" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {data.aiAnalysis ? (
                <div className="prose prose-sm max-w-none">
                  <div className="bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <Sparkles className="w-5 h-5 text-purple-600" />
                      <span className="font-medium text-gray-900">AI Analysis</span>
                    </div>
                    <div className="text-sm text-gray-700 whitespace-pre-wrap">
                      {data.aiAnalysis}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Sparkles className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>AI analysis not available for this metric</p>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between text-xs text-gray-500">
          <span>{data.steps.length} steps in trace</span>
          {data.lastUpdated && (
            <span>Last updated: {data.lastUpdated}</span>
          )}
        </div>
      </div>
    </div>
  )
}
