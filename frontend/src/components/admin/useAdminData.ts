/** Admin data hook – all state, fetch handlers, and effects for the Admin page. */
import { useState, useEffect } from "react"
import { getMyVisitorId } from "@/lib/analytics"
import type {
  SiteKey, AdminUser, DashboardData, SubscribersData, DonationsData,
  AnalyticsSummary, VisitorsData, ClientPortal, ClientPortalApiResponse, LoginResponse,
} from "./admin-types"
import { API_BASE } from "./admin-types"

export type AdminData = ReturnType<typeof useAdminData>

export function useAdminData() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null)

  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loginError, setLoginError] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [cacheClearing, setCacheClearing] = useState(false)
  const [cacheMessage, setCacheMessage] = useState("")

  const [subscribersData, setSubscribersData] = useState<SubscribersData | null>(null)
  const [donationsData, setDonationsData] = useState<DonationsData | null>(null)
  const [analyticsData, setAnalyticsData] = useState<AnalyticsSummary | null>(null)
  const [visitorsData, setVisitorsData] = useState<VisitorsData | null>(null)
  const [clientPortals, setClientPortals] = useState<ClientPortal[]>([])
  const [clientsLoading, setClientsLoading] = useState(false)
  const [clientsError, setClientsError] = useState("")
  const [activeTab, setActiveTab] = useState<"overview" | "analytics" | "subscribers" | "donations">("overview")

  const [activeSite, setActiveSite] = useState<SiteKey>("research")
  const myVisitorId = getMyVisitorId()

  // ── Auth ──
  useEffect(() => {
    const savedToken = localStorage.getItem("admin_token")
    if (savedToken) verifyToken(savedToken)
  }, [])

  const verifyToken = async (tokenToVerify: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/verify`, {
        headers: { "Authorization": `Bearer ${tokenToVerify}`, "Content-Type": "application/json" },
      })
      if (response.ok) {
        const data = await response.json()
        setToken(tokenToVerify)
        setIsAuthenticated(true)
        setAdminUser({ username: data.username, is_admin: data.is_admin })
        fetchDashboard(tokenToVerify)
      } else {
        localStorage.removeItem("admin_token")
        setIsAuthenticated(false)
        setToken(null)
      }
    } catch {
      localStorage.removeItem("admin_token")
      setIsAuthenticated(false)
      setToken(null)
    }
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setLoginError("")
    try {
      const response = await fetch(`${API_BASE}/api/admin/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: username, password }),
      })
      if (response.ok) {
        const data: LoginResponse = await response.json()
        localStorage.setItem("admin_token", data.access_token)
        setToken(data.access_token)
        setIsAuthenticated(true)
        setPassword("")
        verifyToken(data.access_token)
      } else {
        const errorData = await response.json()
        setLoginError(errorData.detail || "Invalid credentials")
      }
    } catch {
      setLoginError("Connection error. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = async () => {
    if (token) {
      try {
        await fetch(`${API_BASE}/api/auth/logout`, {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` },
        })
      } catch {
        // Local credential removal still protects this browser if the server
        // is temporarily unavailable.
      }
    }
    localStorage.removeItem("admin_token")
    setToken(null)
    setIsAuthenticated(false)
    setAdminUser(null)
    setDashboardData(null)
    setClientPortals([])
    setClientsError("")
    setClientsLoading(false)
    setUsername("")
    setPassword("")
  }

  // ── Data fetching ──
  const fetchDashboard = async (authToken: string) => {
    try {
      const r = await fetch(`${API_BASE}/api/admin/dashboard`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (r.ok) setDashboardData(await r.json())
    } catch { console.error("Failed to fetch dashboard data") }
  }

  const fetchSubscribers = async (authToken: string) => {
    try {
      const r = await fetch(`${API_BASE}/api/admin/subscribers`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (r.ok) setSubscribersData(await r.json())
    } catch { console.error("Failed to fetch subscribers") }
  }

  const fetchDonations = async (authToken: string) => {
    try {
      const r = await fetch(`${API_BASE}/api/admin/donations`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (r.ok) setDonationsData(await r.json())
    } catch { console.error("Failed to fetch donations") }
  }

  const fetchAnalytics = async (authToken: string) => {
    try {
      const r = await fetch(`${API_BASE}/api/admin/analytics/summary?days=30`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (r.ok) setAnalyticsData(await r.json())
    } catch { console.error("Failed to fetch analytics") }
  }

  const fetchVisitors = async (authToken: string) => {
    try {
      const r = await fetch(`${API_BASE}/api/admin/analytics/visitors?limit=100`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (r.ok) setVisitorsData(await r.json())
    } catch { console.error("Failed to fetch visitors") }
  }

  const fetchClientPortals = async (authToken: string) => {
    setClientsLoading(true)
    setClientsError("")
    try {
      const response = await fetch(`${API_BASE}/api/admin/clients`, { headers: { "Authorization": `Bearer ${authToken}` } })
      if (!response.ok) { setClientsError("Failed to fetch client portals"); setClientPortals([]); return }
      const data: ClientPortalApiResponse[] = await response.json()
      const rows = Array.isArray(data) ? data : []
      setClientPortals(rows.map((row) => {
        const status: ClientPortal["status"] = row.status === "active" || row.status === "pending" || row.status === "inactive" ? row.status : "pending"
        return { id: String(row.id), name: String(row.name), slug: String(row.slug), description: String(row.description), portalUrl: String(row.portal_url), status, sector: String(row.sector), location: String(row.location), afsl: row.afsl ? String(row.afsl) : undefined, documents: Array.isArray(row.documents) ? row.documents.filter((d) => typeof d === "string") : [] }
      }))
    } catch { setClientsError("Failed to fetch client portals"); setClientPortals([]) } finally { setClientsLoading(false) }
  }

  const blockVisitor = async (visitorId: string, notes?: string) => {
    if (!token) return
    try {
      await fetch(`${API_BASE}/api/admin/analytics/block-visitor?visitor_id=${visitorId}&notes=${encodeURIComponent(notes || "Blocked by admin")}`, { method: "POST", headers: { "Authorization": `Bearer ${token}` } })
      fetchVisitors(token)
      fetchAnalytics(token)
    } catch { console.error("Failed to block visitor") }
  }

  const unblockVisitor = async (visitorId: string) => {
    if (!token) return
    try {
      await fetch(`${API_BASE}/api/admin/analytics/unblock-visitor?visitor_id=${visitorId}`, { method: "POST", headers: { "Authorization": `Bearer ${token}` } })
      fetchVisitors(token)
      fetchAnalytics(token)
    } catch { console.error("Failed to unblock visitor") }
  }

  useEffect(() => {
    if (token) { fetchSubscribers(token); fetchDonations(token); fetchAnalytics(token); fetchVisitors(token); fetchClientPortals(token) }
  }, [token])

  const handleClearCache = async () => {
    if (!token) return
    setCacheClearing(true)
    setCacheMessage("")
    try {
      const r = await fetch(`${API_BASE}/api/admin/cache/clear`, { method: "POST", headers: { "Authorization": `Bearer ${token}` } })
      setCacheMessage(r.ok ? (await r.json()).message : "Failed to clear cache")
    } catch { setCacheMessage("Connection error") } finally { setCacheClearing(false) }
  }

  return {
    // Auth
    isAuthenticated, adminUser,
    // Login form
    username, setUsername, password, setPassword, showPassword, setShowPassword, loginError, isLoading, handleLogin, handleLogout,
    // Dashboard
    dashboardData, cacheClearing, cacheMessage, setCacheMessage, handleClearCache,
    // Data
    subscribersData, donationsData, analyticsData, visitorsData,
    clientPortals, clientsLoading, clientsError,
    // Navigation
    activeTab, setActiveTab, activeSite, setActiveSite,
    // Visitor management
    myVisitorId, blockVisitor, unblockVisitor,
  }
}
