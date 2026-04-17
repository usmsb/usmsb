import { useState } from 'react'
import { Search } from 'lucide-react'
import Badge from '@/components/ui/Badge'
import DataTable from '@/components/ui/DataTable'
import CyberInput from '@/components/ui/CyberInput'
import CyberSelect from '@/components/ui/CyberSelect'
import { useRequests } from '@/hooks/useRequests'
import { formatVibe, formatTime, formatLatency } from '@/lib/utils'
import { useNavigate } from 'react-router-dom'
import type { InferenceRequest } from '@/types/inference'

export default function RequestsPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const { data, isLoading } = useRequests({ page, page_size: 20, status: status || undefined })

  // Mock data
  const mockRequests: InferenceRequest[] = [
    { request_id: 'req_abc123', model_name: 'Qwen-7B', user_wallet: '0x1234567890abcdef', node_id: 'node_001', status: 'running', input_tokens: 150, output_tokens: 200, latency_ms: 523, cost_vibe: 0.000523, created_at: new Date().toISOString() },
    { request_id: 'req_def456', model_name: 'Qwen-14B', user_wallet: '0xabcdef1234567890', node_id: 'node_002', status: 'queued', input_tokens: 320, output_tokens: 0, latency_ms: 0, cost_vibe: 0, created_at: new Date().toISOString() },
    { request_id: 'req_ghi789', model_name: 'CogVideoX', user_wallet: '0xfedcba0987654321', node_id: 'node_003', status: 'completed', input_tokens: 500, output_tokens: 1200, latency_ms: 5200, cost_vibe: 0.022712, created_at: new Date(Date.now() - 60000).toISOString() },
  ]
  const requests = (data?.data?.length ?? 0) > 0 ? data.data : mockRequests

  const columns = [
    { key: 'request_id', header: 'Request ID', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-blue">{r.request_id}</span> },
    { key: 'model_name', header: 'Model', render: (r: InferenceRequest) => <span className="font-rajdhani text-sm">{r.model_name}</span> },
    { key: 'node_id', header: 'Node', render: (r: InferenceRequest) => <span className="font-mono text-xs">{r.node_id}</span> },
    { key: 'status', header: 'Status', render: (r: InferenceRequest) => <Badge status={r.status} dot /> },
    { key: 'tokens', header: 'Tokens', render: (r: InferenceRequest) => <span className="font-mono text-xs">{r.input_tokens + r.output_tokens}</span> },
    { key: 'latency', header: 'Latency', render: (r: InferenceRequest) => <span className="font-mono text-xs text-text-secondary">{r.latency_ms > 0 ? formatLatency(r.latency_ms) : '-'}</span> },
    { key: 'cost', header: 'Cost', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-green">{r.cost_vibe > 0 ? formatVibe(r.cost_vibe) : '-'}</span> },
    { key: 'time', header: 'Time', render: (r: InferenceRequest) => <span className="text-xs text-text-secondary">{formatTime(r.created_at)}</span> },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">INFERENCE REQUESTS</h1>

      <div className="flex gap-4 flex-wrap">
        <div className="flex-1 min-w-[200px] max-w-sm">
          <CyberInput placeholder="Search request ID..." prefixIcon={<Search size={14} className="text-text-secondary" />} />
        </div>
        <CyberSelect
          value={status}
          onChange={e => setStatus(e.target.value)}
          className="min-w-[150px]"
        >
          <option value="">All Status</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </CyberSelect>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-text-secondary">Loading...</div>
      ) : (
        <DataTable columns={columns} data={requests} keyExtractor={r => r.request_id} onRowClick={r => navigate(`/requests/${r.request_id}`)} emptyMessage="No requests found" />
      )}
    </div>
  )
}
