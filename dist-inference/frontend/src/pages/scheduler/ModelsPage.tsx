import { Boxes, Clock } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import DataTable from '@/components/ui/DataTable'
import { useQuery } from '@tanstack/react-query'
import { fetchModels } from '@/lib/api'
import type { ModelInfo } from '@/types/models'

export default function ModelsPage() {
  const { data: models = [], isLoading } = useQuery({
    queryKey: ['models'],
    queryFn: fetchModels,
  })

  // Mock data for demo
  const mockModels: ModelInfo[] = [
    { model_id: '1', name: 'Qwen/Qwen2.5-7B-Instruct', vram_required_gb: 14, gpu_count_needed: 1, is_preloaded: true, loaded_on_nodes: ['node_001', 'node_002'], total_requests: 1234, avg_latency_ms: 523 },
    { model_id: '2', name: 'Qwen/Qwen2.5-14B-Instruct', vram_required_gb: 28, gpu_count_needed: 1, is_preloaded: true, loaded_on_nodes: ['node_001'], total_requests: 567, avg_latency_ms: 1023 },
    { model_id: '3', name: 'Qwen/Qwen2.5-72B-Instruct', vram_required_gb: 160, gpu_count_needed: 4, is_preloaded: false, loaded_on_nodes: [], total_requests: 89, avg_latency_ms: 4120 },
    { model_id: '4', name: 'THUDM/CogVideoX-5b', vram_required_gb: 48, gpu_count_needed: 2, is_preloaded: false, loaded_on_nodes: [], total_requests: 45, avg_latency_ms: 8900 },
    { model_id: '5', name: 'MiniCPM-2B', vram_required_gb: 6, gpu_count_needed: 1, is_preloaded: true, loaded_on_nodes: ['node_001', 'node_002', 'node_003'], total_requests: 2345, avg_latency_ms: 234 },
  ]
  const displayModels = models.length > 0 ? models : mockModels

  const columns = [
    {
      key: 'name',
      header: 'Model',
      render: (row: ModelInfo) => (
        <div>
          <div className="font-rajdhani text-sm text-text-primary">{row.name}</div>
          <div className="text-xs text-text-secondary">{row.gpu_count_needed}x GPU · {row.vram_required_gb}GB VRAM</div>
        </div>
      ),
    },
    {
      key: 'is_preloaded',
      header: 'Status',
      render: (row: ModelInfo) => (
        <span className={row.is_preloaded ? 'text-neon-green text-xs font-rajdhani' : 'text-text-secondary text-xs'}>
          {row.is_preloaded ? '● Preloaded' : '○ Not Preloaded'}
        </span>
      ),
    },
    {
      key: 'loaded_on_nodes',
      header: 'Nodes',
      render: (row: ModelInfo) => (
        <span className="font-mono text-xs text-neon-blue">{row.loaded_on_nodes.length}</span>
      ),
    },
    {
      key: 'total_requests',
      header: 'Total Requests',
      render: (row: ModelInfo) => <span className="font-mono text-xs">{row.total_requests.toLocaleString()}</span>,
    },
    {
      key: 'avg_latency_ms',
      header: 'Avg Latency',
      render: (row: ModelInfo) => <span className="font-mono text-xs text-text-secondary">{row.avg_latency_ms}ms</span>,
    },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">MODEL REGISTRY</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Total Models" value={displayModels.length} icon={<Boxes size={16} />} accent="purple" />
        <MetricCard label="Preloaded" value={displayModels.filter(m => m.is_preloaded).length} icon={<Boxes size={16} />} accent="green" />
        <MetricCard label="Total Requests" value={displayModels.reduce((s, m) => s + m.total_requests, 0).toLocaleString()} icon={<Clock size={16} />} accent="blue" />
      </div>

      <DataTable columns={columns} data={displayModels} keyExtractor={m => m.model_id} emptyMessage="No models registered" />
    </div>
  )
}
