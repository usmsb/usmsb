import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import Badge from '@/components/ui/Badge'
import WalletAddress from '@/components/ui/WalletAddress'
import CyberButton from '@/components/ui/CyberButton'
import { useRequest } from '@/hooks/useRequests'
import { formatVibe, formatLatency, formatDateTime } from '@/lib/utils'

export default function RequestDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: req } = useRequest(id || null)

  // Mock data
  const mockReq = req || {
    request_id: id || 'req_abc123',
    model_name: 'Qwen/Qwen2.5-7B-Instruct',
    user_wallet: '0x1234567890abcdef1234567890abcdef12345678',
    node_id: 'node_001',
    status: 'completed',
    input_tokens: 150,
    output_tokens: 200,
    latency_ms: 523,
    cost_vibe: 0.000523,
    created_at: new Date(Date.now() - 300000).toISOString(),
    completed_at: new Date().toISOString(),
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <CyberButton variant="ghost" size="sm" onClick={() => navigate('/requests')}>
          <ArrowLeft size={16} />
        </CyberButton>
        <h1 className="font-orbitron text-xl font-bold neon-text-blue">
          REQUEST {mockReq.request_id}
        </h1>
        <Badge status={mockReq.status} />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Model', value: mockReq.model_name },
          { label: 'Node', value: mockReq.node_id },
          { label: 'Input Tokens', value: mockReq.input_tokens.toLocaleString() },
          { label: 'Output Tokens', value: mockReq.output_tokens.toLocaleString() },
          { label: 'Latency', value: formatLatency(mockReq.latency_ms) },
          { label: 'Cost', value: `${formatVibe(mockReq.cost_vibe)} VIBE` },
          { label: 'Created', value: formatDateTime(mockReq.created_at) },
          { label: 'Completed', value: mockReq.completed_at ? formatDateTime(mockReq.completed_at) : '-' },
        ].map(item => (
          <div key={item.label} className="cyber-card p-4">
            <div className="text-xs text-text-secondary uppercase tracking-wider mb-1">{item.label}</div>
            <div className="font-mono text-sm text-text-primary">{item.value}</div>
          </div>
        ))}
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-2 tracking-widest">USER WALLET</h3>
        <WalletAddress address={mockReq.user_wallet} chars={8} />
      </div>
    </div>
  )
}
