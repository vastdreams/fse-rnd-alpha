import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"

export function useBacktests() {
  return useQuery({
    queryKey: ["backtests"],
    queryFn: () => api.listBacktests(),
    staleTime: 30 * 1000, // 30 seconds
  })
}

export function useBacktestDetail(id: number | null) {
  return useQuery({
    queryKey: ["backtest", id],
    queryFn: () => api.getBacktest(id!),
    enabled: !!id,
    staleTime: 10 * 1000,
  })
}

export function useRunBacktest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.runBacktest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["backtests"] })
    },
  })
}

