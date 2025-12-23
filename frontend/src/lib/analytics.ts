/**
 * PATH: frontend/src/lib/analytics.ts
 * PURPOSE: Analytics and session tracking for user behavior
 * ROLE IN ARCHITECTURE: Logging layer for page views, interactions, and sessions
 * MAIN EXPORTS:
 *   - analytics: Analytics singleton with tracking methods
 *   - usePageView: Hook for automatic page view tracking
 *   - useSessionTracking: Hook for session management
 * NON-RESPONSIBILITIES:
 *   - Does not handle external analytics providers (GA, Mixpanel)
 *   - Does not persist data to backend (logs to console in dev, could extend to API)
 * NOTES FOR FUTURE AI:
 *   - Extend sendEvent() to POST to /api/analytics endpoint when ready
 *   - Add user identification when auth is implemented
 */

import { useEffect, useRef } from "react"
import { useLocation } from "react-router-dom"

interface AnalyticsEvent {
  type: "page_view" | "click" | "search" | "export" | "session_start" | "session_end" | "interaction"
  timestamp: string
  sessionId: string
  path?: string
  data?: Record<string, unknown>
}

interface Session {
  id: string
  startTime: string
  lastActivity: string
  pageViews: number
  interactions: number
}

class Analytics {
  private sessionId: string
  private session: Session
  private eventQueue: AnalyticsEvent[] = []
  private isProduction: boolean

  constructor() {
    this.isProduction = import.meta.env.PROD
    this.sessionId = this.getOrCreateSessionId()
    this.session = this.initSession()
    
    // Track session start
    this.trackEvent("session_start", { 
      userAgent: navigator.userAgent,
      screenSize: `${window.innerWidth}x${window.innerHeight}`,
      referrer: document.referrer || "direct"
    })

    // Track session end on page unload
    window.addEventListener("beforeunload", () => {
      this.trackEvent("session_end", {
        duration: Date.now() - new Date(this.session.startTime).getTime(),
        pageViews: this.session.pageViews,
        interactions: this.session.interactions
      })
      this.flush()
    })

    // Flush events periodically
    setInterval(() => this.flush(), 30000) // Every 30 seconds
  }

  private getOrCreateSessionId(): string {
    const stored = sessionStorage.getItem("analytics_session_id")
    if (stored) return stored
    
    const newId = `sess_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    sessionStorage.setItem("analytics_session_id", newId)
    return newId
  }

  private initSession(): Session {
    return {
      id: this.sessionId,
      startTime: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
      pageViews: 0,
      interactions: 0
    }
  }

  private sendEvent(event: AnalyticsEvent) {
    // In development, log to console
    if (!this.isProduction) {
      console.log("[Analytics]", event.type, event.path || "", event.data || "")
    }

    // Add to queue for batch sending
    this.eventQueue.push(event)

    // In production, could send to backend:
    // fetch("/api/analytics", { method: "POST", body: JSON.stringify(event) })
  }

  private flush() {
    if (this.eventQueue.length === 0) return
    
    // In production, batch send to backend
    if (this.isProduction && this.eventQueue.length > 0) {
      // Could send batch to /api/analytics/batch
      // For now, just clear the queue
    }
    
    this.eventQueue = []
  }

  trackEvent(type: AnalyticsEvent["type"], data?: Record<string, unknown>) {
    this.session.lastActivity = new Date().toISOString()
    if (type !== "page_view") this.session.interactions++

    this.sendEvent({
      type,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      data
    })
  }

  trackPageView(path: string, title?: string) {
    this.session.pageViews++
    this.session.lastActivity = new Date().toISOString()

    this.sendEvent({
      type: "page_view",
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      path,
      data: { title: title || document.title }
    })
  }

  trackSearch(query: string, resultCount: number) {
    this.trackEvent("search", { query, resultCount })
  }

  trackClick(element: string, context?: Record<string, unknown>) {
    this.trackEvent("click", { element, ...context })
  }

  trackExport(type: string, itemCount: number) {
    this.trackEvent("export", { type, itemCount })
  }

  getSession(): Session {
    return { ...this.session }
  }

  getSessionId(): string {
    return this.sessionId
  }
}

// Singleton instance
export const analytics = new Analytics()

// Hook for automatic page view tracking
export function usePageView() {
  const location = useLocation()
  const previousPath = useRef<string>("")

  useEffect(() => {
    if (location.pathname !== previousPath.current) {
      analytics.trackPageView(location.pathname + location.search)
      previousPath.current = location.pathname
    }
  }, [location])
}

// Hook for session info
export function useSession() {
  return analytics.getSession()
}

