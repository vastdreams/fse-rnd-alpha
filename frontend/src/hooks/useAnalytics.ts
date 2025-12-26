/**
 * PATH: frontend/src/hooks/useAnalytics.ts
 * PURPOSE: Google Analytics 4 tracking hooks for SPA navigation
 * 
 * FEATURES:
 *   - Page view tracking on route changes
 *   - Custom event tracking
 *   - Session duration tracking
 *   - Scroll depth tracking
 * 
 * TRACKING ID: G-3RYSL77PJF
 */

import { useEffect, useCallback } from 'react'
import { useLocation } from 'react-router-dom'

const GA_TRACKING_ID = 'G-3RYSL77PJF'

// Declare gtag on window
declare global {
  interface Window {
    gtag: (...args: unknown[]) => void
    dataLayer: unknown[]
  }
}

/**
 * Track a page view
 */
export function trackPageView(path: string, title?: string) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('config', GA_TRACKING_ID, {
      page_path: path,
      page_title: title || document.title,
    })
  }
}

/**
 * Track a custom event
 */
export function trackEvent(
  action: string,
  category: string,
  label?: string,
  value?: number
) {
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', action, {
      event_category: category,
      event_label: label,
      value: value,
    })
  }
}

/**
 * Track a conversion (form submission, subscription, etc.)
 */
export function trackConversion(conversionName: string, value?: number) {
  trackEvent('conversion', conversionName, undefined, value)
}

/**
 * Track outbound link clicks
 */
export function trackOutboundLink(url: string, label: string) {
  trackEvent('click', 'outbound_link', `${label} (${url})`)
}

/**
 * Track research paper downloads/views
 */
export function trackPaperView(paperId: string, paperTitle: string) {
  trackEvent('view', 'paper', `${paperId}: ${paperTitle}`)
}

/**
 * Track company research views
 */
export function trackCompanyView(ticker: string, companyName: string) {
  trackEvent('view', 'company', `${ticker}: ${companyName}`)
}

/**
 * Track portfolio/ETF interactions
 */
export function trackPortfolioAction(action: string, details?: string) {
  trackEvent(action, 'portfolio', details)
}

/**
 * Hook to track page views on route changes
 */
export function usePageTracking() {
  const location = useLocation()

  useEffect(() => {
    // Track page view on route change
    trackPageView(location.pathname + location.search)
  }, [location])
}

/**
 * Hook to track scroll depth
 */
export function useScrollTracking() {
  useEffect(() => {
    let maxScroll = 0
    const thresholds = [25, 50, 75, 90, 100]
    const trackedThresholds = new Set<number>()

    const handleScroll = () => {
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight
      if (scrollHeight <= 0) return
      
      const scrollPercent = Math.round((window.scrollY / scrollHeight) * 100)

      if (scrollPercent > maxScroll) {
        maxScroll = scrollPercent

        thresholds.forEach((threshold) => {
          if (scrollPercent >= threshold && !trackedThresholds.has(threshold)) {
            trackedThresholds.add(threshold)
            trackEvent('scroll', 'scroll_depth', `${threshold}%`, threshold)
          }
        })
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])
}

/**
 * Hook to track session duration
 */
export function useSessionTracking() {
  useEffect(() => {
    let sessionDuration = 0
    let isVisible = true

    const handleVisibilityChange = () => {
      isVisible = document.visibilityState === 'visible'
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)

    // Send heartbeat every 30 seconds
    const interval = setInterval(() => {
      if (isVisible) {
        sessionDuration += 30
        // Send event every minute
        if (sessionDuration % 60 === 0) {
          trackEvent('timing', 'session_duration', `${sessionDuration}s`, sessionDuration)
        }
      }
    }, 30000)

    // Send final duration on unload
    const handleUnload = () => {
      if (sessionDuration > 0) {
        trackEvent('timing', 'session_duration_final', `${sessionDuration}s`, sessionDuration)
      }
    }

    window.addEventListener('beforeunload', handleUnload)

    return () => {
      clearInterval(interval)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
      window.removeEventListener('beforeunload', handleUnload)
    }
  }, [])
}

/**
 * Combined analytics hook - use this in your App component
 */
export function useAnalytics() {
  usePageTracking()
  useScrollTracking()
  useSessionTracking()
}

/**
 * Hook for tracking button/link clicks
 */
export function useTrackClick() {
  return useCallback((category: string, label: string, action = 'click') => {
    trackEvent(action, category, label)
  }, [])
}

