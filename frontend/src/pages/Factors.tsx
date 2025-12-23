import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useRDSummary } from "@/hooks/useCompanies"
import { formatPercent } from "@/lib/utils"
import { FlaskConical } from "lucide-react"
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts"

export function Factors() {
  const { data: rdSummary, isLoading } = useRDSummary()

  // Get latest year for each company
  const latestByTicker = rdSummary?.reduce((acc, item) => {
    if (!acc[item.ticker] || item.fiscal_year > acc[item.ticker].fiscal_year) {
      acc[item.ticker] = item
    }
    return acc
  }, {} as Record<string, (typeof rdSummary)[0]>)

  const latestData = latestByTicker ? Object.values(latestByTicker) : []

  // Scatter plot data
  const scatterData = latestData
    .filter((d) => d.rd_intensity !== null && d.rd_tone_score !== null)
    .map((d) => ({
      ticker: d.ticker,
      rdIntensity: (d.rd_intensity || 0) * 100,
      toneScore: d.rd_tone_score || 0,
    }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">R&D Factors</h1>
        <p className="text-muted-foreground mt-1">
          Quantitative and text-based R&D analysis
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <FlaskConical className="w-5 h-5 text-purple-400" />
              <div>
                <p className="text-2xl font-bold">{latestData.length}</p>
                <p className="text-sm text-muted-foreground">Companies with R&D Data</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold">
              {latestData.length > 0
                ? formatPercent(
                    latestData.reduce((sum, d) => sum + (d.rd_intensity || 0), 0) /
                      latestData.filter((d) => d.rd_intensity).length
                  )
                : "-"}
            </p>
            <p className="text-sm text-muted-foreground">Avg R&D Intensity</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-2xl font-bold">
              {latestData.length > 0
                ? (
                    latestData.reduce((sum, d) => sum + (d.rd_tone_score || 0), 0) /
                    latestData.filter((d) => d.rd_tone_score).length
                  ).toFixed(2)
                : "-"}
            </p>
            <p className="text-sm text-muted-foreground">Avg Tone Score</p>
          </CardContent>
        </Card>
      </div>

      {/* Scatter Plot */}
      {scatterData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">R&D Intensity vs Tone Score</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400} minHeight={400} debounce={50}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                <XAxis
                  dataKey="rdIntensity"
                  stroke="#888"
                  name="R&D Intensity"
                  unit="%"
                  label={{ value: "R&D Intensity (%)", position: "bottom", fill: "#888" }}
                />
                <YAxis
                  dataKey="toneScore"
                  stroke="#888"
                  name="Tone Score"
                  domain={[0, 1]}
                  label={{ value: "Tone Score", angle: -90, position: "left", fill: "#888" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1a1a2e",
                    border: "1px solid #333",
                    borderRadius: "8px",
                  }}
                  formatter={(value, name) => [
                    name === "rdIntensity" ? `${(value as number).toFixed(2)}%` : (value as number).toFixed(2),
                    name === "rdIntensity" ? "R&D Intensity" : "Tone Score",
                  ]}
                  labelFormatter={(_, payload) => payload[0]?.payload?.ticker || ""}
                />
                <Scatter data={scatterData} fill="#8b5cf6" />
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Data Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">R&D Factor Data (Latest Year)</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Year</TableHead>
                  <TableHead className="text-right">R&D Intensity</TableHead>
                  <TableHead className="text-right">R&D Mentions</TableHead>
                  <TableHead className="text-right">Tone Score</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {latestData
                  .sort((a, b) => (b.rd_intensity || 0) - (a.rd_intensity || 0))
                  .slice(0, 100)
                  .map((item) => (
                    <TableRow key={`${item.ticker}-${item.fiscal_year}`}>
                      <TableCell className="font-medium">{item.ticker}</TableCell>
                      <TableCell>{item.fiscal_year}</TableCell>
                      <TableCell className="text-right text-purple-400">
                        {formatPercent(item.rd_intensity)}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.rd_mentions ?? "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        {item.rd_tone_score?.toFixed(2) ?? "-"}
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

