import { useState, useEffect, useRef } from "react"
import { Search, Menu, X, Mail, Heart } from "lucide-react"
import { Link } from "react-router-dom"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { useAppStore } from "@/store/appStore"
import { useQuery } from "@tanstack/react-query"
import { useSidebar } from "@/components/sidebar-context"
import { useNavigate, useLocation } from "react-router-dom"
import { api } from "@/lib/api"
import { analytics } from "@/lib/analytics"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export function Navbar() {
  const { searchQuery, setSearchQuery } = useAppStore()
  const { isMobile, toggleMobile } = useSidebar()
  const navigate = useNavigate()
  const location = useLocation()
  const [showDropdown, setShowDropdown] = useState(false)
  const [localSearch, setLocalSearch] = useState(searchQuery)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch companies for search dropdown
  const { data: companies } = useQuery({
    queryKey: ["fmpCompanies", null],
    queryFn: () => api.listFMPCompanies(undefined, 500),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Filter companies for dropdown
  const searchResults = localSearch.length >= 1
    ? companies?.filter((c) => {
        const searchLower = localSearch.toLowerCase()
        return (
          c.symbol.toLowerCase().includes(searchLower) ||
          c.name?.toLowerCase().includes(searchLower)
        )
      }).slice(0, 8) // Show max 8 results
    : []

  // Sync local search with global when on Companies page
  useEffect(() => {
    if (location.pathname === "/companies") {
      setLocalSearch(searchQuery)
    }
  }, [searchQuery, location.pathname])

  // Handle search input change
  const handleSearchChange = (value: string) => {
    setLocalSearch(value)
    setShowDropdown(value.length > 0)
    
    // If on Companies page, update global store immediately
    if (location.pathname === "/companies") {
      setSearchQuery(value)
    }
  }

  // Handle search submit (Enter key)
  const handleSearchSubmit = () => {
    setSearchQuery(localSearch)
    setShowDropdown(false)
    analytics.trackSearch(localSearch, searchResults?.length || 0)
    if (location.pathname !== "/companies") {
      navigate("/companies")
    }
  }

  // Handle clicking on a search result
  const handleResultClick = (symbol: string) => {
    analytics.trackClick("search_result", { symbol, query: localSearch })
    setShowDropdown(false)
    setLocalSearch("")
    setSearchQuery("")
    navigate(`/companies/${symbol}`)
  }

  // Handle clicking "View all results"
  const handleViewAll = () => {
    setSearchQuery(localSearch)
    setShowDropdown(false)
    navigate("/companies")
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  const clearSearch = () => {
    setLocalSearch("")
    setSearchQuery("")
    setShowDropdown(false)
    inputRef.current?.focus()
  }

  return (
    <header className="sticky top-0 z-30 h-16 bg-background/80 backdrop-blur-sm border-b border-border">
      <div className="flex items-center justify-between h-full px-4 md:px-6">
        {/* Mobile menu button */}
        {isMobile && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleMobile}
                  className="mr-2 md:hidden"
                >
                  <Menu className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Toggle navigation menu</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            ref={inputRef}
            placeholder="Search companies..."
            value={localSearch}
            onChange={(e) => handleSearchChange(e.target.value)}
            onFocus={() => localSearch.length > 0 && setShowDropdown(true)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSearchSubmit()
              }
              if (e.key === "Escape") {
                setShowDropdown(false)
              }
            }}
            className="pl-10 pr-10 bg-muted border-transparent focus:border-primary"
          />
          {localSearch && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            >
              <X className="w-4 h-4" />
            </button>
          )}

          {/* Search Dropdown */}
          {showDropdown && searchResults && searchResults.length > 0 && (
            <div
              ref={dropdownRef}
              className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg overflow-hidden z-50"
            >
              <div className="max-h-80 overflow-y-auto">
                {searchResults.map((company) => (
                  <button
                    key={company.symbol}
                    onClick={() => handleResultClick(company.symbol)}
                    className="w-full px-4 py-3 text-left hover:bg-muted flex items-center justify-between gap-4 border-b border-border/50 last:border-0"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-primary">
                          {company.symbol}
                        </span>
                        {company.rd_intensity !== null && (
                          <span className="text-xs text-muted-foreground">
                            R&D: {company.rd_intensity.toFixed(1)}%
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-muted-foreground truncate">
                        {company.name}
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {company.sector}
                    </span>
                  </button>
                ))}
              </div>
              {companies && companies.filter((c) => {
                const searchLower = localSearch.toLowerCase()
                return c.symbol.toLowerCase().includes(searchLower) || c.name?.toLowerCase().includes(searchLower)
              }).length > 8 && (
                <button
                  onClick={handleViewAll}
                  className="w-full px-4 py-2 text-sm text-primary hover:bg-muted border-t border-border font-medium"
                >
                  View all results →
                </button>
              )}
            </div>
          )}

          {/* No results message */}
          {showDropdown && localSearch.length > 0 && searchResults?.length === 0 && (
            <div
              ref={dropdownRef}
              className="absolute top-full left-0 right-0 mt-1 bg-popover border border-border rounded-lg shadow-lg p-4 z-50"
            >
              <p className="text-sm text-muted-foreground text-center">
                No companies found for "{localSearch}"
              </p>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-4">
          {/* Subscribe Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link to="/subscribe">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="hidden sm:flex items-center gap-1.5 text-muted-foreground hover:text-emerald-600 dark:hover:text-emerald-400"
                  >
                    <Mail className="w-4 h-4" />
                    <span className="hidden md:inline">Subscribe</span>
                  </Button>
                </Link>
              </TooltipTrigger>
              <TooltipContent>
                <p>Subscribe to research updates</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          {/* Donate Button */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link to="/donate">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="hidden sm:flex items-center gap-1.5 text-muted-foreground hover:text-pink-600 dark:hover:text-pink-400"
                  >
                    <Heart className="w-4 h-4" />
                    <span className="hidden md:inline">Donate</span>
                  </Button>
                </Link>
              </TooltipTrigger>
              <TooltipContent>
                <p>Support free research</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

        </div>
      </div>
    </header>
  )
}
