import { useQuery } from '@tanstack/react-query'
import { fetchRevenueStats, fetchRevenueTrend } from '@/lib/api'

export function useRevenueStats() {
  return useQuery({
    queryKey: ['revenue-stats'],
    queryFn: fetchRevenueStats,
    refetchInterval: 30_000,
  })
}

export function useRevenueTrend(days = 30) {
  return useQuery({
    queryKey: ['revenue-trend', days],
    queryFn: () => fetchRevenueTrend(days),
  })
}
