import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import DataTable from '@/components/ui/DataTable'
import WalletAddress from '@/components/ui/WalletAddress'
import CyberButton from '@/components/ui/CyberButton'
import { formatVibe, timeAgo, formatDateTime } from '@/lib/utils'
import type { InferenceRequest } from '@/types/inference'

export default function UserDetailPage() {
  const { wallet } = useParams<{ wallet: string }>()
  const navigate = useNavigate()

  const mockRequests: InferenceRequest[] = [
    { request_id: 'req_abc123', model_name: 'Qwen-7B', user_wallet: wallet || '', node_id: 'node_001', status: 'completed', input_tokens: 150, output_tokens: 200, latency_ms: 523, cost_vibe: 0.000523, created_at: new Date(Date.now() - 300000).toISOString() },
    { request_id: 'req_def456', model_name: 'Qwen-14B', user_wallet: wallet || '', node_id: 'node_002', status: 'completed', input_tokens: 320, output_tokens: 500, latency_ms: 1023, cost_vibe: 0.001234, created_at: new Date(Date.now() - 600000).toISOString() },
  ]

  const columns = [
    { key: 'request_id', header: 'Request', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-blue">{r.request_id}</span> },
    { key: 'model_name', header: 'Model', render: (r: InferenceRequest) => <span className="font-rajdhani text-sm">{r.model_name}</span> },
    { key: 'status', header: 'Status', render: (r: InferenceRequest) => <span className="text-xs">{r.status}</span> },
    { key: 'cost', header: 'Cost', render: (r: InferenceRequest) => <span className="font-mono text-xs text-neon-green">{formatVibe(r.cost_vibe)}</span> },
    { key: 'time', header: 'Time', render: (r: InferenceRequest) => <span className="text-xs text-text-secondary">{formatDateTime(r.created_at)}</span> },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <CyberButton variant="ghost" size="sm" onClick={() => navigate('/users')}>
          <ArrowLeft size={16} />
        </CyberButton>
        <div>
          <h1 className="font-orbitron text-xl font-bold neon-text-blue">USER DETAIL</h1>
          <WalletAddress address={wallet || ''} chars={8} />
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Balance" value={`${formatVibe(5000)} VIBE`} accent="blue" />
        <MetricCard label="Total Consumption" value={`${formatVibe(1234.56)} VIBE`} accent="green" />
        <MetricCard label="Total Requests" value={567} accent="purple" />
        <MetricCard label="Last Active" value="2 hours ago" accent="blue" />
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">REQUEST HISTORY</h3>
        <DataTable columns={columns} data={mockRequests} keyExtractor={r => r.request_id} emptyMessage="No requests" />
      </div>
    </div>
  )
}
