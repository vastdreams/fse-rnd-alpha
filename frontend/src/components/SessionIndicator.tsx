/**
 * PATH: frontend/src/components/SessionIndicator.tsx
 * PURPOSE: Display current session info and analytics status
 * ROLE IN ARCHITECTURE: UI component for debugging/monitoring
 * MAIN EXPORTS:
 *   - SessionIndicator: Badge showing session info
 * NON-RESPONSIBILITIES:
 *   - Does not manage session (uses analytics singleton)
 * NOTES FOR FUTURE AI:
 *   - Enable only in development or for admin users
 */

import { useEffect, useState } from "react"
import { analytics } from "@/lib/analytics"
import { Activity } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function SessionIndicator() {
  const [session, setSession] = useState(analytics.getSession())
  
  // Update session info periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setSession(analytics.getSession())
    }, 5000) // Update every 5 seconds
    
    return () => clearInterval(interval)
  }, [])

  // Only show in development
  if (import.meta.env.PROD) return null

  const formatDuration = (startTime: string) => {
    const ms = Date.now() - new Date(startTime).getTime()
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    if (minutes < 1) return `${seconds}s`
    return `${minutes}m ${seconds % 60}s`
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="fixed bottom-4 right-4 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs flex items-center gap-2 shadow-lg z-50">
            <Activity className="w-3 h-3 text-green-400 animate-pulse" />
            <span className="text-slate-400">
              Session: <span className="text-slate-200">{session.pageViews} pages</span>
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="left" className="text-xs">
          <div className="space-y-1">
            <p><strong>Session ID:</strong> {session.id.slice(0, 15)}...</p>
            <p><strong>Duration:</strong> {formatDuration(session.startTime)}</p>
            <p><strong>Page Views:</strong> {session.pageViews}</p>
            <p><strong>Interactions:</strong> {session.interactions}</p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

