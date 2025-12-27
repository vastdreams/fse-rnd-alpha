/**
 * PATH: frontend/src/pages/Admin.tsx
 * PURPOSE:
 *   - Admin login and dashboard page
 *   - Secure authentication with JWT tokens
 *   - Admin controls and statistics
 *
 * ROLE IN ARCHITECTURE:
 *   - Protected admin interface for platform management
 *
 * NOTES FOR FUTURE AI:
 *   - Uses localStorage to persist auth token
 *   - Token is validated on each admin action
 *   - Logout clears token and redirects to login
 */

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { 
  Lock, 
  LogIn, 
  LogOut, 
  Shield, 
  Settings, 
  Database, 
  Activity,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
  EyeOff
} from "lucide-react"

// API base URL
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
  actions: Array<{
    name: string
    endpoint: string
  }>
}

export function Admin() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [token, setToken] = useState<string | null>(null)
  const [adminUser, setAdminUser] = useState<AdminUser | null>(null)
  
  // Login form state
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loginError, setLoginError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  
  // Dashboard state
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null)
  const [cacheClearing, setCacheClearing] = useState(false)
  const [cacheMessage, setCacheMessage] = useState("")

  // Check for existing token on mount
  useEffect(() => {
    const savedToken = localStorage.getItem("admin_token")
    if (savedToken) {
      verifyToken(savedToken)
    }
  }, [])

  // Verify token validity
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
        // Token invalid, clear it
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

  // Handle login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setLoginError("")

    try {
      const response = await fetch(`${API_BASE}/api/admin/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username, password }),
      })

      if (response.ok) {
        const data: LoginResponse = await response.json()
        localStorage.setItem("admin_token", data.access_token)
        setToken(data.access_token)
        setIsAuthenticated(true)
        setPassword("") // Clear password from state
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

  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem("admin_token")
    setToken(null)
    setIsAuthenticated(false)
    setAdminUser(null)
    setDashboardData(null)
    setUsername("")
    setPassword("")
  }

  // Fetch dashboard data
  const fetchDashboard = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/admin/dashboard`, {
        headers: {
          "Authorization": `Bearer ${authToken}`,
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const data = await response.json()
        setDashboardData(data)
      }
    } catch {
      console.error("Failed to fetch dashboard data")
    }
  }

  // Clear cache
  const handleClearCache = async () => {
    if (!token) return
    
    setCacheClearing(true)
    setCacheMessage("")

    try {
      const response = await fetch(`${API_BASE}/api/admin/cache/clear`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
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
            <CardDescription>
              Enter your credentials to access the admin dashboard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleLogin} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="username" className="text-sm font-medium">
                  Username
                </label>
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
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
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

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
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
          <p className="text-muted-foreground mt-1">
            Manage your R&D Alpha platform
          </p>
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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Platform</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.stats.platform || "R&D Alpha"}
            </div>
            <p className="text-xs text-muted-foreground">Research Platform</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">API Version</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              v{dashboardData?.stats.api_version || "2.1.0"}
            </div>
            <p className="text-xs text-muted-foreground">Current Release</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">Healthy</div>
            <p className="text-xs text-muted-foreground">All systems operational</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Auth Status</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">Admin</div>
            <p className="text-xs text-muted-foreground">Full access granted</p>
          </CardContent>
        </Card>
      </div>

      {/* Admin Actions */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Cache Management</CardTitle>
            <CardDescription>
              Clear application cache to refresh data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button
              onClick={handleClearCache}
              disabled={cacheClearing}
              variant="outline"
              className="w-full"
            >
              {cacheClearing ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Clearing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <RefreshCw className="w-4 h-4" />
                  Clear Cache
                </span>
              )}
            </Button>
            {cacheMessage && (
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/20 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                {cacheMessage}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Links</CardTitle>
            <CardDescription>
              Navigate to key sections
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-2">
              <a 
                href="/api/docs" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <Database className="w-4 h-4 text-blue-500" />
                <span>API Documentation</span>
              </a>
              <a 
                href="/research" 
                className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <Activity className="w-4 h-4 text-green-500" />
                <span>Research Dashboard</span>
              </a>
              <a 
                href="/portfolio" 
                className="flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors"
              >
                <Settings className="w-4 h-4 text-purple-500" />
                <span>Portfolio Tool</span>
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

