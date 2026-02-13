/**
 * PATH: frontend/src/components/AuditModalContent.tsx
 * PURPOSE: Shared types for Data Audit feature + AuditContextMenu component
 * WHY: Extracted from AuditModal.tsx to stay under 300-line limit.
 */

import { Copy, Database, ExternalLink } from "lucide-react"

// ── Shared types ────────────────────────────────────────────────────

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

export const stepTypeColors: Record<AuditStep["type"], string> = {
  source: "bg-blue-500/10 border-blue-500/30 text-blue-400",
  computation: "bg-purple-500/10 border-purple-500/30 text-purple-400",
  filter: "bg-amber-500/10 border-amber-500/30 text-amber-400",
  aggregation: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
  formula: "bg-pink-500/10 border-pink-500/30 text-pink-400",
  info: "bg-slate-500/10 border-slate-500/30 text-slate-400",
}

// ── AuditContextMenu ────────────────────────────────────────────────

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
      
      {/* Menu - solid white background for readability */}
      <div 
        className="fixed z-50 bg-white border border-gray-200 rounded-lg shadow-xl py-1 min-w-[200px]"
        style={{ left: x, top: y }}
      >
        <button
          onClick={() => { onAudit(); onClose(); }}
          className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-100 flex items-center gap-3 group"
        >
          <Database className="w-4 h-4 text-gray-500 group-hover:text-emerald-600" />
          <div>
            <span className="text-gray-900">Audit Data Point</span>
            <span className="text-xs text-gray-500 ml-2">Chain of Thought</span>
          </div>
        </button>
        
        <div className="h-px bg-gray-200 my-1" />
        
        <button
          onClick={() => { onCopyValue(); onClose(); }}
          className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-3"
        >
          <Copy className="w-4 h-4 text-gray-500" />
          <span className="text-gray-900">Copy Value</span>
        </button>
        
        <button
          onClick={() => { onCopyWithLabel(); onClose(); }}
          className="w-full px-4 py-2 text-left text-sm hover:bg-gray-100 flex items-center gap-3"
        >
          <Copy className="w-4 h-4 text-gray-500" />
          <span className="text-gray-900">Copy with Label</span>
        </button>
        
        <div className="h-px bg-gray-200 my-1" />
        
        <div className="px-4 py-2 text-xs text-gray-400">
          <span>View Source Documents</span>
          <span className="ml-2 text-xs text-gray-300">Soon</span>
        </div>
        <div className="px-4 py-2 text-xs text-gray-400">
          <span>Export to Report</span>
          <span className="ml-2 text-xs text-gray-300">Soon</span>
        </div>
      </div>
    </>
  )
}
