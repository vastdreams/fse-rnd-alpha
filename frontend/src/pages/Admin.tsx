/**
 * PATH: research/frontend/src/pages/Admin.tsx
 * PURPOSE: Unified Admin Dashboard for Finsoeasy properties and clients
 * 
 * WHY: Single admin interface to manage:
 *      - research.finsoeasy.com (R&D Alpha research platform)
 *      - finsoeasy.com (main corporate site)
 *      - Client portals (Oz Premium Finance, EcoJV Project)
 * 
 * FLOW:
 *   ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
 *   │ JWT Login   │───▶│ Site/Client  │───▶│ Dashboard   │
 *   └─────────────┘    │   Select     │    └─────────────┘
 *                      └──────────────┘
 *                            │
 *          ┌─────────────────┼─────────────────┐
 *          ▼                 ▼                 ▼
 *     Research Site    Main Site         Client Portals
 *     (Full API)       (GA4 Only)        (Portal Mgmt)
 * 
 * CLIENTS MANAGED:
 *   - Oz Premium Finance (Australian warehouse credit)
 *   - EcoJV Project (Indonesia/Brunei renewable energy)
 * 
 * DEPENDENCIES:
 *   - JWT auth via backend /api/admin/* endpoints
 *   - GA4 property G-3RYSL77PJF for unified analytics
 */

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { 
  Lock, LogIn, LogOut, Shield, Settings, Database, Activity, RefreshCw,
  CheckCircle, XCircle, Eye, EyeOff, Users, Heart, Mail, DollarSign,
  BarChart3, Clock, Monitor, Smartphone, Globe, Ban, UserX, Building2, FlaskConical, ExternalLink,
  Briefcase, Leaf, CreditCard, FileText, Copy
} from "lucide-react"
import { getMyVisitorId } from "@/lib/analytics"

// Unified GA4 Property ID for all Finsoeasy sites
const UNIFIED_GA4_PROPERTY = "G-3RYSL77PJF"

// Site definitions
type SiteKey = "research" | "main" | "clients"
interface SiteConfig {
  key: SiteKey
  name: string
  domain: string
  icon: React.ReactNode
  hasBackend: boolean
  description: string
}

const SITES: Record<SiteKey, SiteConfig> = {
  research: {
    key: "research",
    name: "R&D Alpha",
    domain: "research.finsoeasy.com",
    icon: <FlaskConical className="w-4 h-4" />,
    hasBackend: true,
    description: "Research platform with full backend access"
  },
  main: {
    key: "main",
    name: "Main Site",
    domain: "finsoeasy.com",
    icon: <Building2 className="w-4 h-4" />,
    hasBackend: false,
    description: "Main website - GA4 analytics only"
  },
  clients: {
    key: "clients",
    name: "Clients",
    domain: "finsoeasy.com",
    icon: <Briefcase className="w-4 h-4" />,
    hasBackend: false,
    description: "Manage client portals and access"
  }
}

// Client portal definitions
interface ClientPortal {
  id: string
  name: string
  slug: string
  description: string
  icon: React.ReactNode
  password: string
  portalUrl: string
  status: "active" | "pending" | "inactive"
  sector: string
  location: string
  afsl?: string
  documents: string[]
}

const CLIENT_PORTALS: ClientPortal[] = [
  {
    id: "ozpremium",
    name: "Oz Premium Finance",
    slug: "ozpremium",
    description: "Warehouse Credit Package - Premium funding trust for insurance premium financing",
    icon: <CreditCard className="w-5 h-5 text-blue-400" />,
    password: "Oz123",
    portalUrl: "https://finsoeasy.com/ozpremium",
    status: "active",
    sector: "Financial Services",
    location: "Sydney, Australia",
    afsl: "556051",
    documents: [
      "Information Memorandum V7a",
      "Warehouse Model (Draft)",
      "Credit Underwriting Policy",
      "AML-CTF Policy",
      "Compliance Plan & Framework"
    ]
  },
  {
    id: "ecojv",
    name: "EcoJV Project",
    slug: "ecojvproject", 
    description: "Indonesia/Brunei renewable energy joint venture - Solar and sustainability infrastructure",
    icon: <Leaf className="w-5 h-5 text-green-400" />,
    password: "eco",
    portalUrl: "https://finsoeasy.com/ecojvproject",
    status: "active",
    sector: "Renewable Energy",
    location: "Indonesia / Brunei",
    documents: [
      "Investor Deck",
      "Project Overview",
      "JV Structure"
    ]
  }
]

const API_BASE = import.meta.env.VITE_API_URL || ""

interface AdminUser {
  username: string
  is_admin: boolean
}

interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
}

interface DashboardData {
  message: string
  timestamp: string
  stats: {
    api_version: string
    platform: string
  }
}

interface Subscriber {
  email: string
  source: string
  first_name: string | null
  last_name: string | null
  profession: string | null
  subscribed_at: string
}

interface Donation {
  email: string
  amount: number
  is_recurring: boolean
  stripe_session_id: string
  created_at: string
}

interface SubscribersData {
  count: number
  subscribers: Subscriber[]
}

interface DonationsData {
  count: number
  total_amount: number
  donations: Donation[]
}

interface AnalyticsSummary {
  period_days: number
  totals: {
    views: number
    unique_visitors: number
    sessions: number
    avg_duration_seconds: number
  }
  pages: Array<{
    page: string
    views: number
    unique_visitors: number
    avg_duration: number
  }>
  daily: Array<{
    date: string
    views: number
    unique_visitors: number
  }>
  devices: Record<string, number>
}

interface Visitor {
  visitor_id: string
  first_seen: string
  last_seen: string
  total_visits: number
  is_blocked: boolean
  notes: string | null
  last_ip: string
  device: string
}

interface VisitorsData {
  count: number
  visitors: Visitor[]
}

export function Admin() {
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
  const [activeTab, setActiveTab] = useState<"overview" | "analytics" | "subscribers" | "donations">("overview")
  
  // Site selector state - allows switching between Finsoeasy properties
  const [activeSite, setActiveSite] = useState<SiteKey>("research")
  const currentSite = SITES[activeSite]

  const myVisitorId = getMyVisitorId()

  useEffect(() => {
    const savedToken = localStorage.getItem("admin_token")
    if (savedToken) {
      verifyToken(savedToken)
    }
  }, [])

  const verifyToken = async (tokenToVerify: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/verify`, {
        headers: {
          "Authorization": `Bearer ${tokenToVerify}`,
          "Content-Type": "application/json",
        },
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
        body: JSON.stringify({ username, password }),
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

  const handleLogout = () => {
    localStorage.removeItem("admin_token")
    setToken(null)
    setIsAuthenticated(false)
    setAdminUser(null)
    setDashboardData(null)
    setUsername("")
    setPassword("")
  }

  const fetchDashboard = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/dashboard`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      })
      if (response.ok) {
        const data = await response.json()
        setDashboardData(data)
      }
    } catch {
      console.error("Failed to fetch dashboard data")
    }
  }

  const fetchSubscribers = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/subscribers`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      })
      if (response.ok) {
        const data = await response.json()
        setSubscribersData(data)
      }
    } catch {
      console.error("Failed to fetch subscribers")
    }
  }

  const fetchDonations = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/donations`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      })
      if (response.ok) {
        const data = await response.json()
        setDonationsData(data)
      }
    } catch {
      console.error("Failed to fetch donations")
    }
  }

  const fetchAnalytics = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/analytics/summary?days=30`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      })
      if (response.ok) {
        const data = await response.json()
        setAnalyticsData(data)
      }
    } catch {
      console.error("Failed to fetch analytics")
    }
  }

  const fetchVisitors = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/analytics/visitors?limit=100`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      })
      if (response.ok) {
        const data = await response.json()
        setVisitorsData(data)
      }
    } catch {
      console.error("Failed to fetch visitors")
    }
  }

  const blockVisitor = async (visitorId: string, notes?: string) => {
    if (!token) return
    try {
      await fetch(`${API_BASE}/api/admin/analytics/block-visitor?visitor_id=${visitorId}&notes=${encodeURIComponent(notes || "Blocked by admin")}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
      })
      fetchVisitors(token)
      fetchAnalytics(token)
    } catch {
      console.error("Failed to block visitor")
    }
  }

  const unblockVisitor = async (visitorId: string) => {
    if (!token) return
    try {
      await fetch(`${API_BASE}/api/admin/analytics/unblock-visitor?visitor_id=${visitorId}`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
      })
      fetchVisitors(token)
      fetchAnalytics(token)
    } catch {
      console.error("Failed to unblock visitor")
    }
  }

  useEffect(() => {
    if (token) {
      fetchSubscribers(token)
      fetchDonations(token)
      fetchAnalytics(token)
      fetchVisitors(token)
    }
  }, [token])

  const handleClearCache = async () => {
    if (!token) return
    setCacheClearing(true)
    setCacheMessage("")

    try {
      const response = await fetch(`${API_BASE}/api/admin/cache/clear`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
      })
      if (response.ok) {
        const data = await response.json()
        setCacheMessage(data.message)
      } else {
        setCacheMessage("Failed to clear cache")
      }
    } catch {
      setCacheMessage("Connection error")
    } finally {
      setCacheClearing(false)
    }
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${Math.round(seconds)}s`
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return `${mins}m ${secs}s`
  }

  // Login form
  if (!isAuthenticated) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <CardTitle className="text-2xl">Admin Login</CardTitle>
            <CardDescription>Enter your credentials to access the admin dashboard</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="username" className="text-sm font-medium">Username</label>
                <Input
                  id="username"
                  type="text"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>
              
              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">Password</label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {loginError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-sm flex items-center gap-2">
                  <XCircle className="w-4 h-4" />
                  {loginError}
                </div>
              )}

              <Button type="submit" className="w-full" disabled={isLoading}>
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Signing in...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <LogIn className="w-4 h-4" />
                    Sign In
                  </span>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Admin dashboard
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-500" />
            Unified Admin Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">Manage all Finsoeasy properties</p>
        </div>
        <div className="flex items-center gap-4">
          <Badge variant="outline" className="px-3 py-1">
            <Lock className="w-3 h-3 mr-2" />
            {adminUser?.username}
          </Badge>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>
      </div>

      {/* Site Selector */}
      <Card className="bg-gradient-to-r from-slate-900/50 to-slate-800/50 border-slate-700">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Globe className="w-4 h-4" />
              <span>Select Property:</span>
            </div>
            <div className="flex gap-2">
              {Object.values(SITES).map((site) => (
                <Button
                  key={site.key}
                  variant={activeSite === site.key ? "default" : "outline"}
                  size="sm"
                  onClick={() => setActiveSite(site.key)}
                  className={activeSite === site.key 
                    ? "bg-blue-600 hover:bg-blue-700" 
                    : "hover:bg-slate-700"
                  }
                >
                  {site.icon}
                  <span className="ml-2">{site.name}</span>
                  {!site.hasBackend && (
                    <Badge variant="secondary" className="ml-2 text-[10px] px-1">GA4</Badge>
                  )}
                </Button>
              ))}
            </div>
            <a 
              href={`https://${currentSite.domain}`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-blue-400 transition-colors"
            >
              {currentSite.domain}
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </CardContent>
      </Card>

      {/* Welcome Card - Context aware */}
      <Card className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                {currentSite.icon}
                <span className="font-semibold text-lg">
                  {currentSite.name} Dashboard
                </span>
                {currentSite.hasBackend && dashboardData && (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                )}
              </div>
              <p className="text-sm text-muted-foreground">
                {currentSite.description}
              </p>
            </div>
            <Badge variant="outline" className="text-xs">
              GA4: {UNIFIED_GA4_PROPERTY}
            </Badge>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid - Research Site (with backend) */}
      {activeSite === "research" && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          <Card className="cursor-pointer hover:border-blue-500 transition-colors" onClick={() => setActiveTab("analytics")}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Page Views</CardTitle>
              <BarChart3 className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-500">{analyticsData?.totals.views || 0}</div>
              <p className="text-xs text-muted-foreground">Last 30 days</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:border-purple-500 transition-colors" onClick={() => setActiveTab("analytics")}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Visitors</CardTitle>
              <Globe className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-500">{analyticsData?.totals.unique_visitors || 0}</div>
              <p className="text-xs text-muted-foreground">Unique visitors</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:border-emerald-500 transition-colors" onClick={() => setActiveTab("subscribers")}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Subscribers</CardTitle>
              <Users className="h-4 w-4 text-emerald-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-emerald-500">{subscribersData?.count || 0}</div>
              <p className="text-xs text-muted-foreground">Newsletter signups</p>
            </CardContent>
          </Card>

          <Card className="cursor-pointer hover:border-pink-500 transition-colors" onClick={() => setActiveTab("donations")}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Donations</CardTitle>
              <Heart className="h-4 w-4 text-pink-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-pink-500">${donationsData?.total_amount?.toFixed(2) || "0.00"}</div>
              <p className="text-xs text-muted-foreground">{donationsData?.count || 0} donations</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg. Time</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-orange-500">
                {formatDuration(analyticsData?.totals.avg_duration_seconds || 0)}
              </div>
              <p className="text-xs text-muted-foreground">Per page</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Site Dashboard - GA4 Only */}
      {activeSite === "main" && (
        <div className="space-y-6">
          {/* GA4 Integration Status */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="border-amber-500/30 bg-amber-500/5">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">GA4 Status</CardTitle>
                <Activity className="h-4 w-4 text-amber-500" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-semibold text-amber-500">Pending Setup</div>
                <p className="text-xs text-muted-foreground">Add tracking code to site</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Property ID</CardTitle>
                <BarChart3 className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-mono font-semibold text-blue-500">{UNIFIED_GA4_PROPERTY}</div>
                <p className="text-xs text-muted-foreground">Shared with research site</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Server</CardTitle>
                <Monitor className="h-4 w-4 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-lg font-mono font-semibold text-purple-500">13.210.239.75</div>
                <p className="text-xs text-muted-foreground">Sydney (ap-southeast-2)</p>
              </CardContent>
            </Card>
          </div>

          {/* GA4 Setup Instructions */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="w-5 h-5 text-blue-500" />
                GA4 Tracking Setup for finsoeasy.com
              </CardTitle>
              <CardDescription>
                Add unified analytics tracking to the main site
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 bg-slate-900/50 rounded-lg border border-slate-700">
                <p className="text-xs text-muted-foreground mb-2">Add this to the &lt;head&gt; section:</p>
                <pre className="text-xs font-mono text-green-400 overflow-x-auto whitespace-pre-wrap">
{`<!-- Google Analytics - Unified Finsoeasy Property -->
<script async src="https://www.googletagmanager.com/gtag/js?id=${UNIFIED_GA4_PROPERTY}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', '${UNIFIED_GA4_PROPERTY}', {
    'cookie_domain': '.finsoeasy.com'
  });
</script>`}
                </pre>
              </div>

              <div className="flex gap-3">
                <Button variant="outline" asChild>
                  <a 
                    href="https://analytics.google.com/analytics/web/#/report-home/a123456789w123456789p123456789" 
                    target="_blank" 
                    rel="noopener noreferrer"
                  >
                    <BarChart3 className="w-4 h-4 mr-2" />
                    Open GA4 Dashboard
                    <ExternalLink className="w-3 h-3 ml-2" />
                  </a>
                </Button>
                <Button 
                  variant="outline"
                  onClick={() => {
                    navigator.clipboard.writeText(UNIFIED_GA4_PROPERTY)
                    setCacheMessage("Copied GA4 ID!")
                    setTimeout(() => setCacheMessage(""), 2000)
                  }}
                >
                  Copy Property ID
                </Button>
              </div>
              
              {cacheMessage && (
                <div className="p-2 rounded bg-green-500/10 border border-green-500/20 text-green-400 text-sm">
                  {cacheMessage}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Quick Links for Main Site */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Deployment Info</CardTitle>
                <CardDescription>Main site server details</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between p-2 rounded bg-muted">
                  <span className="text-sm">EC2 Instance</span>
                  <code className="text-xs font-mono">i-0fa8fcc0259caa8e9</code>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted">
                  <span className="text-sm">Region</span>
                  <code className="text-xs font-mono">ap-southeast-2</code>
                </div>
                <div className="flex items-center justify-between p-2 rounded bg-muted">
                  <span className="text-sm">SSH Key</span>
                  <code className="text-xs font-mono">finsoeasy-key.pem</code>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>View Combined Analytics</CardTitle>
                <CardDescription>See data from both sites in GA4</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Once tracking is added, view combined analytics by:
                </p>
                <ol className="text-sm space-y-2 list-decimal list-inside text-muted-foreground">
                  <li>Go to GA4 → Reports → Engagement</li>
                  <li>Add comparison by Hostname</li>
                  <li>Compare research.finsoeasy.com vs finsoeasy.com</li>
                </ol>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Clients Dashboard */}
      {activeSite === "clients" && (
        <div className="space-y-6">
          {/* Client Summary Cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Active Clients</CardTitle>
                <Briefcase className="h-4 w-4 text-emerald-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-emerald-500">
                  {CLIENT_PORTALS.filter(c => c.status === "active").length}
                </div>
                <p className="text-xs text-muted-foreground">With live investor portals</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
                <FileText className="h-4 w-4 text-blue-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-blue-500">
                  {CLIENT_PORTALS.reduce((acc, c) => acc + c.documents.length, 0)}
                </div>
                <p className="text-xs text-muted-foreground">Across all client portals</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">Sectors</CardTitle>
                <Globe className="h-4 w-4 text-purple-500" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-purple-500">
                  {new Set(CLIENT_PORTALS.map(c => c.sector)).size}
                </div>
                <p className="text-xs text-muted-foreground">Financial Services, Renewables</p>
              </CardContent>
            </Card>
          </div>

          {/* Client Portals List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-blue-500" />
                Client Portals
              </CardTitle>
              <CardDescription>Manage investor portals and access credentials</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {CLIENT_PORTALS.map((client) => (
                  <div 
                    key={client.id}
                    className="p-4 rounded-lg border border-slate-700 bg-slate-900/50 hover:border-slate-600 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 rounded-xl bg-slate-800 flex items-center justify-center">
                          {client.icon}
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-lg">{client.name}</h3>
                            <Badge 
                              variant={client.status === "active" ? "default" : "secondary"}
                              className={client.status === "active" ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : ""}
                            >
                              {client.status}
                            </Badge>
                            {client.afsl && (
                              <Badge variant="outline" className="text-xs">
                                AFSL {client.afsl}
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">{client.description}</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Globe className="w-3 h-3" />
                              {client.location}
                            </span>
                            <span className="flex items-center gap-1">
                              <FileText className="w-3 h-3" />
                              {client.documents.length} documents
                            </span>
                          </div>
                        </div>
                      </div>
                      <div className="flex flex-col gap-2">
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => window.open(client.portalUrl, '_blank')}
                        >
                          <ExternalLink className="w-3 h-3 mr-1" />
                          View Portal
                        </Button>
                      </div>
                    </div>

                    {/* Credentials Section */}
                    <div className="mt-4 pt-4 border-t border-slate-700/50">
                      <div className="grid gap-3 md:grid-cols-2">
                        <div className="p-3 rounded-lg bg-slate-800/50">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Portal URL</p>
                              <code className="text-sm font-mono text-blue-400">{client.portalUrl}</code>
                            </div>
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => {
                                navigator.clipboard.writeText(client.portalUrl)
                                setCacheMessage(`Copied ${client.name} URL!`)
                                setTimeout(() => setCacheMessage(""), 2000)
                              }}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                        <div className="p-3 rounded-lg bg-slate-800/50">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="text-xs text-muted-foreground mb-1">Access Password</p>
                              <code className="text-sm font-mono text-amber-400">{client.password}</code>
                            </div>
                            <Button 
                              size="sm" 
                              variant="ghost"
                              onClick={() => {
                                navigator.clipboard.writeText(client.password)
                                setCacheMessage(`Copied ${client.name} password!`)
                                setTimeout(() => setCacheMessage(""), 2000)
                              }}
                            >
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Documents List */}
                    <div className="mt-4 pt-4 border-t border-slate-700/50">
                      <p className="text-xs text-muted-foreground mb-2">Available Documents:</p>
                      <div className="flex flex-wrap gap-2">
                        {client.documents.map((doc, i) => (
                          <Badge key={i} variant="outline" className="text-xs">
                            <FileText className="w-3 h-3 mr-1" />
                            {doc}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Access Control</CardTitle>
                <CardDescription>Manage client portal credentials</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Client passwords are stored in the main finsoeasy.com codebase:
                </p>
                <div className="p-3 bg-slate-800/50 rounded-lg">
                  <code className="text-xs text-muted-foreground">
                    /src/app/ozpremium/page.tsx<br/>
                    /src/app/ecojvproject/page.tsx
                  </code>
                </div>
                <p className="text-xs text-muted-foreground">
                  To change passwords, update the CORRECT_PASSWORD constant in each file and redeploy.
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Add New Client</CardTitle>
                <CardDescription>Steps to onboard a new investor portal</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <ol className="text-sm space-y-2 list-decimal list-inside text-muted-foreground">
                  <li>Create investor deck (HTML or embedded doc)</li>
                  <li>Add route in <code className="text-xs">/src/app/[client]/page.tsx</code></li>
                  <li>Set password protection</li>
                  <li>Deploy and test portal access</li>
                  <li>Update this admin (CLIENT_PORTALS array)</li>
                </ol>
              </CardContent>
            </Card>
          </div>

          {/* Copy Notification */}
          {cacheMessage && (
            <div className="fixed bottom-4 right-4 p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-400 text-sm flex items-center gap-2 animate-in slide-in-from-bottom-4">
              <CheckCircle className="w-4 h-4" />
              {cacheMessage}
            </div>
          )}
        </div>
      )}

      {/* Tab Navigation - Research Site Only */}
      {activeSite === "research" && (
        <div className="flex gap-2 border-b overflow-x-auto">
          <Button variant={activeTab === "overview" ? "default" : "ghost"} onClick={() => setActiveTab("overview")} className="rounded-b-none">
            <Settings className="w-4 h-4 mr-2" />
            Overview
          </Button>
          <Button variant={activeTab === "analytics" ? "default" : "ghost"} onClick={() => setActiveTab("analytics")} className="rounded-b-none">
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </Button>
          <Button variant={activeTab === "subscribers" ? "default" : "ghost"} onClick={() => setActiveTab("subscribers")} className="rounded-b-none">
            <Users className="w-4 h-4 mr-2" />
            Subscribers ({subscribersData?.count || 0})
          </Button>
          <Button variant={activeTab === "donations" ? "default" : "ghost"} onClick={() => setActiveTab("donations")} className="rounded-b-none">
            <Heart className="w-4 h-4 mr-2" />
            Donations ({donationsData?.count || 0})
          </Button>
        </div>
      )}

      {/* Tab Content - Research Site Only */}
      {activeSite === "research" && activeTab === "overview" && (
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Cache Management</CardTitle>
              <CardDescription>Clear application cache to refresh data</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
              <Button onClick={handleClearCache} disabled={cacheClearing} variant="outline" className="w-full">
              {cacheClearing ? (
                  <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4 animate-spin" />Clearing...</span>
              ) : (
                  <span className="flex items-center gap-2"><RefreshCw className="w-4 h-4" />Clear Cache</span>
              )}
            </Button>
            {cacheMessage && (
                <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 text-sm flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                {cacheMessage}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Links</CardTitle>
              <CardDescription>Navigate to key sections</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-2">
                <a href="/api/docs" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors">
                  <Database className="w-4 h-4 text-blue-500" />
                  <span>API Documentation</span>
                </a>
                <a href="/" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors">
                  <Activity className="w-4 h-4 text-green-500" />
                  <span>Main Paper</span>
                </a>
                <a href="/portfolio" className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors">
                  <Settings className="w-4 h-4 text-purple-500" />
                  <span>R&D ETF</span>
                </a>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeSite === "research" && activeTab === "analytics" && (
        <div className="space-y-6">
          {/* Page Views by Page */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-blue-500" />
                Page Views (Last 30 Days)
              </CardTitle>
              <CardDescription>Traffic breakdown by page</CardDescription>
            </CardHeader>
            <CardContent>
              {analyticsData?.pages && analyticsData.pages.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Page</TableHead>
                      <TableHead className="text-right">Views</TableHead>
                      <TableHead className="text-right">Unique Visitors</TableHead>
                      <TableHead className="text-right">Avg. Duration</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {analyticsData.pages.map((page, i) => (
                      <TableRow key={i}>
                        <TableCell className="font-mono text-sm">{page.page}</TableCell>
                        <TableCell className="text-right font-semibold">{page.views}</TableCell>
                        <TableCell className="text-right">{page.unique_visitors}</TableCell>
                        <TableCell className="text-right text-muted-foreground">{formatDuration(page.avg_duration)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No page view data yet</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Device Breakdown */}
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Device Breakdown</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {analyticsData?.devices && Object.entries(analyticsData.devices).map(([device, count]) => (
                    <div key={device} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {device === "desktop" ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                        <span className="capitalize">{device}</span>
                      </div>
                      <Badge variant="outline">{count}</Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Your Visitor ID */}
            <Card>
              <CardHeader>
                <CardTitle>Your Visitor ID</CardTitle>
                <CardDescription>Block this to exclude yourself from analytics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="p-3 bg-muted rounded-lg font-mono text-sm break-all mb-4">
                  {myVisitorId}
                </div>
                <Button 
                  variant="outline" 
                  className="w-full"
                  onClick={() => blockVisitor(myVisitorId, "Admin - self excluded")}
                >
                  <UserX className="w-4 h-4 mr-2" />
                  Exclude Myself from Analytics
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Visitors List */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-purple-500" />
                Visitors
              </CardTitle>
              <CardDescription>{visitorsData?.count || 0} total visitors tracked</CardDescription>
            </CardHeader>
            <CardContent>
              {visitorsData?.visitors && visitorsData.visitors.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Visitor ID</TableHead>
                      <TableHead>Device</TableHead>
                      <TableHead className="text-right">Visits</TableHead>
                      <TableHead>Last Seen</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {visitorsData.visitors.map((visitor) => (
                      <TableRow key={visitor.visitor_id} className={visitor.is_blocked ? "opacity-50" : ""}>
                        <TableCell className="font-mono text-xs">
                          {visitor.visitor_id.slice(0, 12)}...
                          {visitor.visitor_id === myVisitorId && (
                            <Badge className="ml-2" variant="secondary">You</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {visitor.device === "desktop" ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
                        </TableCell>
                        <TableCell className="text-right font-semibold">{visitor.total_visits}</TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {visitor.last_seen ? new Date(visitor.last_seen).toLocaleString() : "N/A"}
                        </TableCell>
                        <TableCell>
                          {visitor.is_blocked ? (
                            <Badge variant="destructive">Blocked</Badge>
                          ) : (
                            <Badge variant="outline">Active</Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {visitor.is_blocked ? (
                            <Button size="sm" variant="ghost" onClick={() => unblockVisitor(visitor.visitor_id)}>
                              Unblock
                            </Button>
                          ) : (
                            <Button size="sm" variant="ghost" onClick={() => blockVisitor(visitor.visitor_id)}>
                              <Ban className="w-3 h-3" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Globe className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No visitors tracked yet</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {activeSite === "research" && activeTab === "subscribers" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Mail className="w-5 h-5 text-emerald-500" />
              Newsletter Subscribers
            </CardTitle>
            <CardDescription>{subscribersData?.count || 0} total subscribers</CardDescription>
          </CardHeader>
          <CardContent>
            {subscribersData?.subscribers && subscribersData.subscribers.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>First Name</TableHead>
                    <TableHead>Last Name</TableHead>
                    <TableHead>Profession</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Subscribed At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subscribersData.subscribers.map((sub, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{sub.email}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.first_name || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.last_name || "-"}</TableCell>
                      <TableCell className="text-muted-foreground">{sub.profession || "-"}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="capitalize">
                          {sub.source?.replace(/_/g, " ") || "website"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(sub.subscribed_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Users className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No subscribers yet</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {activeSite === "research" && activeTab === "donations" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-pink-500" />
              Donations History
            </CardTitle>
            <CardDescription>
              {donationsData?.count || 0} donations totaling ${donationsData?.total_amount?.toFixed(2) || "0.00"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {donationsData?.donations && donationsData.donations.length > 0 ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Date</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {donationsData.donations.map((donation, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{donation.email}</TableCell>
                      <TableCell className="text-emerald-600 font-semibold">${donation.amount.toFixed(2)}</TableCell>
                      <TableCell>
                        <Badge variant={donation.is_recurring ? "default" : "outline"}>
                          {donation.is_recurring ? "Monthly" : "One-time"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(donation.created_at).toLocaleString()}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <Heart className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No donations yet</p>
            </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
