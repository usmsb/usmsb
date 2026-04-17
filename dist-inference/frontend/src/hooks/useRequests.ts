import { useQuery } from '@tanstack/react-query'
import { fetchRequests, fetchRequest } from '@/lib/api'

export function useRequests(params?: { page?: number; page_size?: number; status?: string }) {
  return useQuery({
    queryKey: ['requests', params],
    queryFn: () => fetchRequests(params),
    refetchInterval: 5_000,
  })
}

export function useRequest(id: string | null) {
  return useQuery({
    queryKey: ['request', id],
    queryFn: () => fetchRequest(id!),
    enabled: !!id,
  })
}
