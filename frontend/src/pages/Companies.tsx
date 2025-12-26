import { useQuery } from "@tanstack/react-query"
import { Link } from "react-router-dom"
import { api } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Search, Building2, TrendingUp, FlaskConical, Download } from "lucide-react"
import { Button } from "@/components/ui/button"
import { exportToCSV } from "@/lib/export"
import { useAppStore } from "@/store/appStore"
import { analytics } from "@/lib/analytics"

export function Companies() {
  // Use global search from app store (synced with navbar)
  const { searchQuery, setSearchQuery, sectorFilter, setSectorFilter } = useAppStore()

  const { data: companies, isLoading } = useQuery({
    queryKey: ["fmpCompanies", sectorFilter],
    queryFn: () => api.listFMPCompanies(sectorFilter || undefined, 500),
  })

  const { data: sectors } = useQuery({
    queryKey: ["sectors"],
    queryFn: api.getSectors,
  })

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "..."
    if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`
    if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`
    if (num >= 1e6) return `$${(num / 1e6).toFixed(0)}M`
    return `$${num.toLocaleString()}`
  }

  const filteredCompanies = companies?.filter((c) => {
    const searchLower = searchQuery.toLowerCase()
    return (
      c.symbol.toLowerCase().includes(searchLower) ||
      c.name?.toLowerCase().includes(searchLower)
    )
  })

  const handleExportCSV = () => {
    if (!filteredCompanies || filteredCompanies.length === 0) return
    
    analytics.trackExport("companies_csv", filteredCompanies.length)
    exportToCSV(
      filteredCompanies.map(c => ({
        symbol: c.symbol,
        name: c.name || "",
        sector: c.sector || "",
        rd_intensity: c.rd_intensity?.toFixed(2) || "",
        latest_rd_expense: c.latest_rd_expense || 0,
        latest_revenue: c.latest_revenue || 0,
      })),
      `sp500_companies_${sectorFilter || "all"}_${new Date().toISOString().split("T")[0]}.csv`,
      [
        { key: "symbol", header: "Symbol" },
        { key: "name", header: "Company Name" },
        { key: "sector", header: "Sector" },
        { key: "rd_intensity", header: "R&D Intensity (%)" },
        { key: "latest_rd_expense", header: "R&D Expense ($)" },
        { key: "latest_revenue", header: "Revenue ($)" },
      ]
    )
  }

  const getSectorColor = (sector: string | null) => {
    const colors: Record<string, string> = {
      "Technology": "bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-400",
      "Healthcare": "bg-green-100 dark:bg-green-500/20 text-green-700 dark:text-green-400",
      "Financials": "bg-yellow-100 dark:bg-yellow-500/20 text-yellow-700 dark:text-yellow-400",
      "Consumer Discretionary": "bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-400",
      "Industrials": "bg-orange-100 dark:bg-orange-500/20 text-orange-700 dark:text-orange-400",
      "Communication Services": "bg-pink-100 dark:bg-pink-500/20 text-pink-700 dark:text-pink-400",
      "Consumer Staples": "bg-teal-100 dark:bg-teal-500/20 text-teal-700 dark:text-teal-400",
      "Energy": "bg-red-100 dark:bg-red-500/20 text-red-700 dark:text-red-400",
      "Utilities": "bg-cyan-100 dark:bg-cyan-500/20 text-cyan-700 dark:text-cyan-400",
      "Materials": "bg-amber-100 dark:bg-amber-500/20 text-amber-700 dark:text-amber-400",
      "Real Estate": "bg-indigo-100 dark:bg-indigo-500/20 text-indigo-700 dark:text-indigo-400",
    }
    return colors[sector || ""] || "bg-gray-100 dark:bg-gray-500/20 text-gray-700 dark:text-gray-400"
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-muted-foreground animate-pulse">Loading companies...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">S&P 500 Companies</h1>
          <p className="text-muted-foreground">{companies?.length} companies with financial data</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExportCSV}
          disabled={!filteredCompanies || filteredCompanies.length === 0}
        >
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-4">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by symbol or name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            variant={sectorFilter === null ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setSectorFilter(null)}
          >
            All Sectors
          </Badge>
          {sectors?.map((s) => (
            <Badge
              key={s.sector}
              variant={sectorFilter === s.sector ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setSectorFilter(s.sector)}
            >
              {s.sector} ({s.count})
            </Badge>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Companies</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{filteredCompanies?.length}</div>
            {searchQuery && (
              <p className="text-xs text-muted-foreground">
                Filtered from {companies?.length}
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">With R&D Data</CardTitle>
            <FlaskConical className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {filteredCompanies?.filter(c => c.rd_intensity !== null).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg R&D Intensity</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {((filteredCompanies?.reduce((acc, c) => acc + (c.rd_intensity || 0), 0) ?? 0) / 
                (filteredCompanies?.filter(c => c.rd_intensity).length || 1)).toFixed(1)}%
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Companies Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-24">Symbol</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Sector</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">R&D Expense</TableHead>
                <TableHead className="text-right">R&D Intensity</TableHead>
                <TableHead className="text-right">Years</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredCompanies?.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                    No companies found matching "{searchQuery}"
                  </TableCell>
                </TableRow>
              ) : (
                filteredCompanies?.map((company) => (
                <TableRow key={company.symbol} className="hover:bg-muted/50">
                  <TableCell>
                    <Link 
                      to={`/companies/${company.symbol}`} 
                      className="font-mono font-bold text-primary hover:underline"
                    >
                      {company.symbol}
                    </Link>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate">
                    {company.name}
                  </TableCell>
                  <TableCell>
                    <Badge className={getSectorColor(company.sector)} variant="outline">
                        {company.sector || "..."}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatNumber(company.latest_revenue)}
                  </TableCell>
                  <TableCell className="text-right font-mono">
                    {formatNumber(company.latest_rd_expense)}
                  </TableCell>
                  <TableCell className="text-right">
                    {company.rd_intensity !== null ? (
                      <span className={`font-bold ${company.rd_intensity > 10 ? 'text-green-600 dark:text-green-400' : company.rd_intensity > 5 ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground'}`}>
                        {company.rd_intensity.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {company.years_data}
                  </TableCell>
                </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
