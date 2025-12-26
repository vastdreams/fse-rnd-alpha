import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatNumber(num: number | null | undefined, decimals = 2): string {
  if (num === null || num === undefined) return "..."
  if (Math.abs(num) >= 1e12) return `$${(num / 1e12).toFixed(decimals)}T`
  if (Math.abs(num) >= 1e9) return `$${(num / 1e9).toFixed(decimals)}B`
  if (Math.abs(num) >= 1e6) return `$${(num / 1e6).toFixed(decimals)}M`
  if (Math.abs(num) >= 1e3) return `$${(num / 1e3).toFixed(decimals)}K`
  return `$${num.toFixed(decimals)}`
}

export function formatPercent(num: number | null | undefined, decimals = 1): string {
  if (num === null || num === undefined) return "..."
  return `${(num * 100).toFixed(decimals)}%`
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "..."
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

