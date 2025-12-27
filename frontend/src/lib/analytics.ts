/**
 * Analytics and Session Tracking
 * 
 * Tracks page views, session duration, and user behavior.
 * Integrates with both Google Analytics and our PostgreSQL backend.
 * 
 * Publication: https://research.finsoeasy.com
 */

import { useEffect, useRef } from "react"
import { useLocation } from "react-router-dom"

const API_BASE = import.meta.env.VITE_API_URL || ''
const GA_TRACKING_ID = 'G-3RYSL77PJF'

declare global {
  interface Window {
    gtag: (...args: unknown[]) => void
    dataLayer: unknown[]
  }
}

// Generate or retrieve visitor ID (persisted in localStorage)
function getVisitorId(): string {
  const key = 'rd_alpha_visitor_id'
  let visitorId = localStorage.getItem(key)
  
  if (!visitorId) {
    visitorId = 'v_' + Math.random().toString(36).substring(2) + Date.now().toString(36)
    localStorage.setItem(key, visitorId)
  }
  
  return visitorId
}

// Generate session ID (persisted for browser session)
function getSessionId(): string {
  const key = 'rd_alpha_session_id'
  let sessionId = sessionStorage.getItem(key)
  
  if (!sessionId) {
    sessionId = 's_' + Math.random().toString(36).substring(2) + Date.now().toString(36)
    sessionStorage.setItem(key, sessionId)
  }
  
  return sessionId
}

// Send page view to Google Analytics
function gaTrackPageView(path: string, title?: string) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('config', GA_TRACKING_ID, {
      page_path: path,
      page_title: title || document.title,
    })
  }
}

// Send custom event to Google Analytics
function gaTrackEvent(action: string, category: string, label?: string, value?: number) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
      value: value,
    })
  }
}

// Send page view to backend
async function backendTrackPageView(pagePath: string, pageTitle?: string): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/analytics/pageview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        page_path: pagePath,
        page_title: pageTitle || document.title,
        referrer: document.referrer || undefined,
        session_id: getSessionId(),
        visitor_id: getVisitorId(),
      }),
    })
  } catch (error) {
    // Silently fail - analytics should not break the app
    console.debug('Backend analytics tracking failed:', error)
  }
}

// Update duration on backend
async function backendUpdateDuration(pagePath: string, duration: number): Promise<void> {
  try {
    const data = JSON.stringify({
      session_id: getSessionId(),
      page_path: pagePath,
      duration_seconds: Math.round(duration),
    })
    
    // Use sendBeacon for reliable delivery on page unload
    if (navigator.sendBeacon) {
      navigator.sendBeacon(`${API_BASE}/api/analytics/duration`, data)
    } else {
      await fetch(`${API_BASE}/api/analytics/duration`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: data,
      })
    }
  } catch (error) {
    console.debug('Duration update failed:', error)
  }
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
  private visitorId: string
  private session: Session
  private currentPath: string = ''
  private pageStartTime: number = Date.now()
  private isProduction: boolean

  constructor() {
    this.isProduction = import.meta.env.PROD
    this.sessionId = getSessionId()
    this.visitorId = getVisitorId()
    this.session = this.initSession()

    // Track session end and duration on page unload
    window.addEventListener("beforeunload", () => {
      if (this.currentPath) {
        const duration = (Date.now() - this.pageStartTime) / 1000
        backendUpdateDuration(this.currentPath, duration)
      }
    })

    // Track when tab becomes hidden
    document.addEventListener("visibilitychange", () => {
      if (document.hidden && this.currentPath) {
        const duration = (Date.now() - this.pageStartTime) / 1000
        backendUpdateDuration(this.currentPath, duration)
      }
    })
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

  trackPageView(path: string, title?: string) {
    // Update duration for previous page
    if (this.currentPath && this.currentPath !== path) {
      const duration = (Date.now() - this.pageStartTime) / 1000
      backendUpdateDuration(this.currentPath, duration)
    }

    this.session.pageViews++
    this.session.lastActivity = new Date().toISOString()
    this.currentPath = path
    this.pageStartTime = Date.now()

    // Send to backend PostgreSQL
    backendTrackPageView(path, title)
    
    // Send to Google Analytics
    gaTrackPageView(path, title)

    if (!this.isProduction) {
      console.log("[Analytics] Page view:", path)
    }
  }

  trackSearch(query: string, resultCount: number) {
    this.session.interactions++
    gaTrackEvent("search", "search", query, resultCount)
  }

  trackClick(element: string, _context?: Record<string, unknown>) {
    this.session.interactions++
    gaTrackEvent("click", "interaction", element)
  }

  trackExport(type: string, itemCount: number) {
    this.session.interactions++
    gaTrackEvent("export", "data_export", type, itemCount)
  }
  
  trackPaperView(paperId: string, paperTitle: string) {
    this.session.interactions++
    gaTrackEvent("view", "paper", `${paperId}: ${paperTitle}`)
  }
  
  trackCompanyView(ticker: string, companyName: string) {
    this.session.interactions++
    gaTrackEvent("view", "company", `${ticker}: ${companyName}`)
  }
  
  trackPortfolioAction(action: string, details?: string) {
    this.session.interactions++
    gaTrackEvent(action, "portfolio", details)
  }

  getSession(): Session {
    return { ...this.session }
  }

  getSessionId(): string {
    return this.sessionId
  }

  getVisitorId(): string {
    return this.visitorId
  }
}

// Singleton instance
export const analytics = new Analytics()

// Hook for automatic page view tracking
export function usePageView() {
  const location = useLocation()
  const previousPath = useRef<string>("")

  useEffect(() => {
    const currentPath = location.pathname + location.search
    if (currentPath !== previousPath.current) {
      analytics.trackPageView(currentPath)
      previousPath.current = currentPath
    }
  }, [location])
}

// Hook for session info
export function useSession() {
  return analytics.getSession()
}

// Get visitor ID for admin to identify themselves
export function getMyVisitorId(): string {
  return analytics.getVisitorId()
}
