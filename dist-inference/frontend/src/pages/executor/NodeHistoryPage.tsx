import MetricCard from '@/components/ui/MetricCard'
import DataTable from '@/components/ui/DataTable'
import Badge from '@/components/ui/Badge'
import { formatVibe, formatLatency, formatDateTime } from '@/lib/utils'
import type { InferenceRequest } from '@/types/inference'

export default function NodeHistoryPage() {
  const mockHistory: InferenceRequest[] = [
    { request_id: 'req_abc123', model_name: 'Qwen-7B', user_wallet: '0x1234567890abcdef', node_id: 'node_001', status: 'completed', input_tokens: 150, output_tokens: 200, latency_ms: 523, cost_vibe: 0.000523, created_at: new Date().toISOString() },
    { request_id: 'req_def456', model_name: 'Qwen-7B', user_wallet: '0xabcdef1234567890', node_id: 'node_001', status: 'completed', input_tokens: 320, output_tokens: 500, latency_ms: 612, cost_vibe: 0.000612, created_at: new Date(Date.now() - 120000).toISOString() },
    { request_id: 'req_ghi789', model_name: 'Qwen-14B', user_wallet: '0xfedcba0987654321', node_id: 'node_001', status: 'completed', input_tokens: 500, output_tokens: 1200, latency_ms: 1234, cost_vibe: 0.001234, created_at: new Date(Date.now() - 300000).toISOString() },
    { request_id: 'req_jkl012', model_name: 'CogVideoX', user_wallet: '0x1234567890abcdef', node_id: 'node_001', status: 'failed', input_tokens: 0, output_tokens: 0, latency_ms: 0, cost_vibe: 0, created_at: new Date(Date.now() - 600000).toISOString(), error: 'Out of memory' },
  ]

  const columns = [
    { key: 'request_id', header: 'Request ID', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-blue">{r.request_id}</span> },
    { key: 'model', header: 'Model', render: (r: InferenceRequest) => <span className="font-rajdhani text-sm">{r.model_name}</span> },
    { key: 'status', header: 'Status', render: (r: InferenceRequest) => <Badge status={r.status} dot /> },
    { key: 'tokens', header: 'Tokens', render: (r: InferenceRequest) => <span className="font-mono text-xs">{r.input_tokens + r.output_tokens}</span> },
    { key: 'latency', header: 'Latency', render: (r: InferenceRequest) => <span className="font-mono text-xs text-text-secondary">{r.latency_ms > 0 ? formatLatency(r.latency_ms) : '-'}</span> },
    { key: 'cost', header: 'Earnings', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-green">{r.cost_vibe > 0 ? formatVibe(r.cost_vibe) : '-'}</span> },
    { key: 'time', header: 'Time', render: (r: InferenceRequest) => <span className="text-xs text-text-secondary">{formatDateTime(r.created_at)}</span> },
  ]

  const totalRequests = mockHistory.length
  const successRate = Math.round(((mockHistory.filter(r => r.status === 'completed').length) / totalRequests) * 100)
  const avgLatency = Math.round(mockHistory.filter(r => r.latency_ms > 0).reduce((s, r) => s + r.latency_ms, 0) / mockHistory.filter(r => r.latency_ms > 0).length)

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">INFERENCE HISTORY</h1>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Total Requests" value={totalRequests} accent="blue" />
        <MetricCard label="Success Rate" value={`${successRate}%`} accent="green" />
        <MetricCard label="Avg Latency" value={`${avgLatency}ms`} accent="purple" />
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">HISTORY</h3>
        <DataTable columns={columns} data={mockHistory} keyExtractor={r => r.request_id} emptyMessage="No history" />
      </div>
    </div>
  )
}
