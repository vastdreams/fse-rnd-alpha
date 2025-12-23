import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useCompanies(limit = 100, offset = 0) {
  return useQuery({
    queryKey: ["companies", limit, offset],
    queryFn: () => api.listCompanies(limit, offset),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export function useCompanyDetail(ticker: string | null) {
  return useQuery({
    queryKey: ["company", ticker],
    queryFn: () => api.getCompany(ticker!),
    enabled: !!ticker,
    staleTime: 5 * 60 * 1000,
  })
}

export function useRDSummary() {
  return useQuery({
    queryKey: ["rd-summary"],
    queryFn: () => api.getRDSummary(),
    staleTime: 5 * 60 * 1000,
  })
}

export function useStatsSummary() {
  return useQuery({
    queryKey: ["stats-summary"],
    queryFn: () => api.getStatsSummary(),
    staleTime: 60 * 1000, // 1 minute
  })
}

export function useUnifiedFilings(limit = 500, offset = 0) {
  return useQuery({
    queryKey: ["unified-filings", limit, offset],
    queryFn: async () => {
      const result = await api.getUnifiedFilings(limit, offset)
      return result.rows
    },
    staleTime: 5 * 60 * 1000,
  })
}

