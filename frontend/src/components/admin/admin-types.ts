/** Shared types, constants, and helpers for the Admin dashboard. */
import type { ReactNode } from "react"

// Unified GA4 Property ID for all Finsoeasy sites
export const UNIFIED_GA4_PROPERTY = "G-3RYSL77PJF"
export const API_BASE = import.meta.env.VITE_API_URL || ""

export type SiteKey = "research" | "main" | "clients"

export interface SiteConfig {
  key: SiteKey
  name: string
  domain: string
  icon: ReactNode
  hasBackend: boolean
  description: string
}

export interface ClientPortal {
  id: string
  name: string
  slug: string
  description: string
  portalUrl: string
  status: "active" | "pending" | "inactive"
  sector: string
  location: string
  afsl?: string
  documents: string[]
}

export interface ClientPortalApiResponse {
  id: string
  name: string
  slug: string
  description: string
  portal_url: string
  status: "active" | "pending" | "inactive"
  sector: string
  location: string
  afsl?: string | null
  documents: string[]
}

export interface AdminUser {
  username: string
  is_admin: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface DashboardData {
  message: string
  timestamp: string
  stats: { api_version: string; platform: string }
}

export interface Subscriber {
  email: string
  source: string
  first_name: string | null
  last_name: string | null
  profession: string | null
  subscribed_at: string
}

export interface Donation {
  email: string
  amount: number
  is_recurring: boolean
  stripe_session_id: string
  created_at: string
}

export interface SubscribersData {
  count: number
  subscribers: Subscriber[]
}

export interface DonationsData {
  count: number
  total_amount: number
  donations: Donation[]
}

export interface AnalyticsSummary {
  period_days: number
  totals: { views: number; unique_visitors: number; sessions: number; avg_duration_seconds: number }
  pages: Array<{ page: string; views: number; unique_visitors: number; avg_duration: number }>
  daily: Array<{ date: string; views: number; unique_visitors: number }>
  devices: Record<string, number>
}

export interface Visitor {
  visitor_id: string
  first_seen: string
  last_seen: string
  total_visits: number
  is_blocked: boolean
  notes: string | null
  last_ip: string
  device: string
}

export interface VisitorsData {
  count: number
  visitors: Visitor[]
}

export const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${Math.round(seconds)}s`
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return `${mins}m ${secs}s`
}
