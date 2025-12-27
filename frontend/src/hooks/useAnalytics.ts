/**
 * Analytics Tracking Hook
 * 
 * Tracks page views and time spent on each page.
 * Data stored in PostgreSQL for persistence.
 */

import { useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || ''

// Generate or retrieve visitor ID (persisted in localStorage)
function getVisitorId(): string {
  const key = 'rd_alpha_visitor_id'
  let visitorId = localStorage.getItem(key)
  
  if (!visitorId) {
    // Generate a unique visitor ID
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

interface TrackingData {
  page_path: string
  page_title?: string
  referrer?: string
  session_id: string
  visitor_id: string
}

async function trackPageView(data: TrackingData): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/analytics/pageview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  } catch (error) {
    // Silently fail - analytics should not break the app
    console.debug('Analytics tracking failed:', error)
  }
}

async function updateDuration(sessionId: string, pagePath: string, duration: number): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/analytics/duration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        page_path: pagePath,
        duration_seconds: Math.round(duration),
      }),
    })
  } catch (error) {
    console.debug('Duration update failed:', error)
  }
}

export function useAnalytics() {
  const location = useLocation()
  const startTimeRef = useRef<number>(Date.now())
  const currentPathRef = useRef<string>(location.pathname)
  const sessionId = useRef<string>(getSessionId())
  const visitorId = useRef<string>(getVisitorId())

  // Track page view on location change
  useEffect(() => {
    const pagePath = location.pathname + location.search
    
    // Update duration for previous page
    if (currentPathRef.current && currentPathRef.current !== pagePath) {
      const duration = (Date.now() - startTimeRef.current) / 1000
      updateDuration(sessionId.current, currentPathRef.current, duration)
    }
    
    // Track new page view
    trackPageView({
      page_path: pagePath,
      page_title: document.title,
      referrer: document.referrer || undefined,
      session_id: sessionId.current,
      visitor_id: visitorId.current,
    })
    
    // Reset timer for new page
    startTimeRef.current = Date.now()
    currentPathRef.current = pagePath
  }, [location.pathname, location.search])

  // Track duration when user leaves the page
  useEffect(() => {
    const handleBeforeUnload = () => {
      const duration = (Date.now() - startTimeRef.current) / 1000
      // Use sendBeacon for reliable delivery on page unload
      const data = JSON.stringify({
        session_id: sessionId.current,
        page_path: currentPathRef.current,
        duration_seconds: Math.round(duration),
      })
      navigator.sendBeacon(`${API_BASE}/api/analytics/duration`, data)
    }

    // Also track when tab becomes hidden
    const handleVisibilityChange = () => {
      if (document.hidden) {
        const duration = (Date.now() - startTimeRef.current) / 1000
        updateDuration(sessionId.current, currentPathRef.current, duration)
      }
    }

    window.addEventListener('beforeunload', handleBeforeUnload)
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [])

  // Expose visitor ID for admin to identify themselves
  const getMyVisitorId = useCallback(() => visitorId.current, [])

  return { getMyVisitorId }
}

// Component wrapper for easy integration
export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  useAnalytics()
  return <>{children}</>
}
