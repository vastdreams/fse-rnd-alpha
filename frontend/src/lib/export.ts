/**
 * Utility functions for exporting data to various formats
 */

/**
 * Convert an array of objects to CSV string
 */
export function arrayToCSV<T extends Record<string, unknown>>(
  data: T[],
  columns?: { key: keyof T; header: string }[]
): string {
  if (data.length === 0) return ""

  // Determine columns from data if not provided
  const cols = columns || Object.keys(data[0]).map((key) => ({
    key: key as keyof T,
    header: String(key),
  }))

  // Create header row
  const headerRow = cols.map((col) => `"${col.header}"`).join(",")

  // Create data rows
  const dataRows = data.map((row) =>
    cols
      .map((col) => {
        const value = row[col.key]
        if (value === null || value === undefined) return ""
        if (typeof value === "string") return `"${value.replace(/"/g, '""')}"`
        if (typeof value === "number") return String(value)
        return `"${String(value).replace(/"/g, '""')}"`
      })
      .join(",")
  )

  return [headerRow, ...dataRows].join("\n")
}

/**
 * Download a string as a file
 */
export function downloadAsFile(content: string, filename: string, mimeType: string = "text/csv") {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement("a")
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

/**
 * Export an array of objects as a CSV file
 */
export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  filename: string,
  columns?: { key: keyof T; header: string }[]
) {
  const csv = arrayToCSV(data, columns)
  downloadAsFile(csv, filename, "text/csv;charset=utf-8")
}

/**
 * Export data as JSON file
 */
export function exportToJSON<T>(data: T, filename: string) {
  const json = JSON.stringify(data, null, 2)
  downloadAsFile(json, filename, "application/json")
}

