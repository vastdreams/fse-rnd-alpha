import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useBacktests, useRunBacktest } from "@/hooks/useBacktest"
import { Play, Clock, CheckCircle, XCircle } from "lucide-react"

export function Backtests() {
  const { data: backtests, isLoading } = useBacktests()
  const runBacktest = useRunBacktest()

  const [factorId, setFactorId] = useState("rd_intensity")
  const [startYear, setStartYear] = useState(2010)
  const [endYear, setEndYear] = useState(2024)

  const handleRunBacktest = () => {
    runBacktest.mutate({
      factor_id: factorId,
      universe: ["AAPL", "MSFT", "GOOGL", "META", "NVDA"], // Example
      start_year: startYear,
      end_year: endYear,
    })
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="w-4 h-4 text-green-400" />
      case "running":
        return <Clock className="w-4 h-4 text-yellow-400 animate-spin" />
      case "failed":
        return <XCircle className="w-4 h-4 text-red-400" />
      default:
        return <Clock className="w-4 h-4 text-muted-foreground" />
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Backtests</h1>
        <p className="text-muted-foreground mt-1">
          Portfolio backtesting based on R&D factors
        </p>
      </div>

      {/* New Backtest Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Run New Backtest</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">
                Factor
              </label>
              <select
                value={factorId}
                onChange={(e) => setFactorId(e.target.value)}
                className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
              >
                <option value="rd_intensity">R&D Intensity</option>
                <option value="rd_tone_score">R&D Tone Score</option>
                <option value="rd_mentions">R&D Mentions</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">
                Start Year
              </label>
              <Input
                type="number"
                value={startYear}
                onChange={(e) => setStartYear(parseInt(e.target.value))}
                min={2000}
                max={2024}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-1 block">
                End Year
              </label>
              <Input
                type="number"
                value={endYear}
                onChange={(e) => setEndYear(parseInt(e.target.value))}
                min={2000}
                max={2024}
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleRunBacktest}
                disabled={runBacktest.isPending}
                className="w-full"
              >
                <Play className="w-4 h-4 mr-2" />
                {runBacktest.isPending ? "Running..." : "Run Backtest"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backtest History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Backtest History</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center text-muted-foreground py-8">Loading...</div>
          ) : backtests?.length === 0 ? (
            <div className="text-center text-muted-foreground py-8">
              No backtests run yet. Create one above!
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Factor</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {backtests?.map((bt) => (
                  <TableRow key={bt.id}>
                    <TableCell className="font-medium">{bt.name}</TableCell>
                    <TableCell>{bt.factor_id}</TableCell>
                    <TableCell>
                      {bt.start_year} - {bt.end_year}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {getStatusIcon(bt.status)}
                        <span>{bt.status}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      {new Date(bt.created_at).toLocaleDateString()}
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

