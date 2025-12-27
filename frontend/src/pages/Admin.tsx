/**
 * Admin Dashboard
 * 
 * Secure admin interface for platform management.
 * Includes analytics, subscribers, and donations tracking.
 * 
 * Publication: https://research.finsoeasy.com
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
  BarChart3, Clock, Monitor, Smartphone, Globe, Ban, UserX
} from "lucide-react"
import { getMyVisitorId } from "@/lib/analytics"

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
            Admin Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">Manage your R&D Alpha platform</p>
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

      {/* Welcome Card */}
      {dashboardData && (
        <Card className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-5 h-5 text-green-500" />
              <span className="font-semibold text-lg">{dashboardData.message}</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Last login: {new Date(dashboardData.timestamp).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Stats Grid */}
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

      {/* Tab Navigation */}
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

      {/* Tab Content */}
      {activeTab === "overview" && (
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

      {activeTab === "analytics" && (
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

      {activeTab === "subscribers" && (
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
                    <TableHead>Source</TableHead>
                    <TableHead>Subscribed At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {subscribersData.subscribers.map((sub, i) => (
                    <TableRow key={i}>
                      <TableCell className="font-medium">{sub.email}</TableCell>
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

      {activeTab === "donations" && (
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
