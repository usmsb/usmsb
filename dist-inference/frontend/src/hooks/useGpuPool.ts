import { useQuery } from '@tanstack/react-query'
import { fetchGpuPool, fetchNode } from '@/lib/api'
import { useGpuPoolStore } from '@/stores/gpuPoolStore'

export function useGpuPool() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['gpu-pool'],
    queryFn: fetchGpuPool,
    refetchInterval: 10_000, // refresh every 10s as backup
  })

  const store = useGpuPoolStore()
  if (data) {
    store.setNodes(data.nodes ?? data ?? [])
  }

  return { data, isLoading, error, refetch }
}

export function useNode(nodeId: string | null) {
  return useQuery({
    queryKey: ['node', nodeId],
    queryFn: () => fetchNode(nodeId!),
    enabled: !!nodeId,
    refetchInterval: 5_000,
  })
}
