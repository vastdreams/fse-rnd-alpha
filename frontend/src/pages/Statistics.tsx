import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useStatsSummary, useUnifiedFilings } from "@/hooks/useCompanies"
import { Download, Database } from "lucide-react"

export function Statistics() {
  const { data: stats, isLoading: statsLoading } = useStatsSummary()
  const { data: filings, isLoading: filingsLoading } = useUnifiedFilings(500)

  const handleExport = () => {
    if (!filings) return

    const headers = [
      "ticker",
      "name",
      "cik",
      "fiscal_year",
      "filing_date",
      "file_format",
      "file_size_bytes",
      "extraction_status",
    ]

    const csv = [
      headers.join(","),
      ...filings.map((f) =>
        [
          f.ticker,
          `"${f.name || ""}"`,
          f.cik,
          f.fiscal_year,
          f.filing_date || "",
          f.file_format || "",
          f.file_size_bytes || "",
          f.extraction_status || "",
        ].join(",")
      ),
    ].join("\n")

    const blob = new Blob([csv], { type: "text/csv" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "unified_filings.csv"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Statistics</h1>
          <p className="text-muted-foreground mt-1">
            Database overview and unified filings
          </p>
        </div>
        <Button onClick={handleExport} disabled={!filings?.length}>
          <Download className="w-4 h-4 mr-2" />
          Export CSV
        </Button>
      </div>

      {/* Database Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Database className="w-5 h-5" />
            Database Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <div className="text-center text-muted-foreground py-4">Loading...</div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">{stats?.companies?.total?.toLocaleString()}</p>
                <p className="text-sm text-muted-foreground">Companies</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {stats?.company_years?.total?.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Company Years</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {stats?.company_years?.with_financials?.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">With Financials</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {stats?.company_years?.with_text_factors?.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">With R&D Factors</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {stats?.annual_reports?.total?.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Annual Reports</p>
              </div>
              <div className="p-4 bg-muted rounded-lg">
                <p className="text-2xl font-bold">
                  {stats?.prices?.total_records?.toLocaleString()}
                </p>
                <p className="text-sm text-muted-foreground">Price Points</p>
              </div>
              <div className="p-4 bg-muted rounded-lg col-span-2">
                <p className="text-2xl font-bold">
                  {stats?.prices?.unique_tickers || 0} Tickers
                </p>
                <p className="text-sm text-muted-foreground">With Price Data</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Unified Filings Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">
            Unified Filings ({filings?.length || 0} rows)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {filingsLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <div className="max-h-[600px] overflow-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-card">
                  <TableRow>
                    <TableHead>Ticker</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>CIK</TableHead>
                    <TableHead>Year</TableHead>
                    <TableHead>Filing Date</TableHead>
                    <TableHead>Format</TableHead>
                    <TableHead className="text-right">Size</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filings?.map((filing) => (
                    <TableRow key={filing.company_year_id}>
                      <TableCell className="font-medium">{filing.ticker}</TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {filing.name || "-"}
                      </TableCell>
                      <TableCell>{filing.cik}</TableCell>
                      <TableCell>{filing.fiscal_year}</TableCell>
                      <TableCell>{filing.filing_date || "-"}</TableCell>
                      <TableCell>{filing.file_format || "-"}</TableCell>
                      <TableCell className="text-right">
                        {filing.file_size_bytes
                          ? `${(filing.file_size_bytes / 1024 / 1024).toFixed(1)} MB`
                          : "-"}
                      </TableCell>
                      <TableCell>
                        <span
                          className={`px-2 py-0.5 text-xs rounded ${
                            filing.extraction_status === "complete"
                              ? "bg-green-500/20 text-green-400"
                              : filing.extraction_status === "pending"
                              ? "bg-yellow-500/20 text-yellow-400"
                              : "bg-muted text-muted-foreground"
                          }`}
                        >
                          {filing.extraction_status || "-"}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

