import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Cpu, Zap, DollarSign } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import Badge from '@/components/ui/Badge'
import ProgressBar from '@/components/ui/ProgressBar'
import WalletAddress from '@/components/ui/WalletAddress'
import CyberButton from '@/components/ui/CyberButton'
import { useNode } from '@/hooks/useGpuPool'
import { formatVibe, formatLatency, timeAgo, pct } from '@/lib/utils'
import type { GpuInfo } from '@/types/gpu'

export default function NodeDetailPage() {
  const { nodeId } = useParams<{ nodeId: string }>()
  const navigate = useNavigate()
  const { data: node, isLoading } = useNode(nodeId || null)

  // Mock data
  const mockNode = node || {
    node_id: nodeId || 'node_001',
    wallet_address: '0x1234567890abcdef1234567890abcdef12345678',
    ip_address: '192.168.1.100:8080',
    status: 'busy',
    gpu_count: 4,
    gpus: [
      { index: 0, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 38, temperature_c: 72, power_w: 280, utilization_percent: 95, status: 'busy' },
      { index: 1, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 28, temperature_c: 68, power_w: 250, utilization_percent: 70, status: 'busy' },
      { index: 2, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 12, temperature_c: 55, power_w: 180, utilization_percent: 30, status: 'idle' },
      { index: 3, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 0, temperature_c: 40, power_w: 50, utilization_percent: 0, status: 'idle' },
    ],
    models: [
      { name: 'Qwen/Qwen2.5-7B-Instruct', vram_required_gb: 14, loaded: true, loaded_at: new Date().toISOString(), total_requests: 156, total_tokens: 45678 },
      { name: 'Qwen/Qwen2.5-14B-Instruct', vram_required_gb: 28, loaded: true, loaded_at: new Date().toISOString(), total_requests: 89, total_tokens: 23456 },
    ],
    last_heartbeat: new Date(Date.now() - 5000).toISOString(),
    today_earnings: 234.56,
    total_earnings: 12345.67,
    registered_at: new Date(Date.now() - 86400000 * 30).toISOString(),
  }

  if (isLoading) return <div className="text-center py-20 text-text-secondary">Loading...</div>

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <CyberButton variant="ghost" size="sm" onClick={() => navigate('/nodes')}>
          <ArrowLeft size={16} />
        </CyberButton>
        <div className="flex-1">
          <h1 className="font-orbitron text-xl font-bold neon-text-blue">{mockNode.node_id}</h1>
          <WalletAddress address={mockNode.wallet_address} />
        </div>
        <Badge status={mockNode.status} />
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="GPUs" value={mockNode.gpu_count} icon={<Cpu size={16} />} accent="blue" />
        <MetricCard label="Today Earnings" value={formatVibe(mockNode.today_earnings)} subValue="VIBE" icon={<DollarSign size={16} />} accent="green" />
        <MetricCard label="Total Earnings" value={formatVibe(mockNode.total_earnings)} subValue="VIBE" icon={<DollarSign size={16} />} accent="purple" />
        <MetricCard label="Last Heartbeat" value={timeAgo(mockNode.last_heartbeat)} icon={<Zap size={16} />} accent="blue" />
      </div>

      {/* GPU Grid */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">GPU STATUS</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockNode.gpus.map((gpu: GpuInfo) => (
            <div key={gpu.index} className="p-4 bg-black/20 rounded-lg border border-cyber-border">
              <div className="flex items-center justify-between mb-3">
                <span className="font-orbitron text-sm text-neon-blue">{gpu.name}</span>
                <Badge status={gpu.status} />
              </div>
              <div className="mb-3">
                <ProgressBar used={gpu.vram_used_gb} total={gpu.vram_total_gb} label={`VRAM: ${gpu.vram_used_gb}GB / ${gpu.vram_total_gb}GB`} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                <div>
                  <div className="text-text-secondary">Temp</div>
                  <div className={gpu.temperature_c > 80 ? 'text-neon-red' : 'text-text-primary'}>{gpu.temperature_c}°C</div>
                </div>
                <div>
                  <div className="text-text-secondary">Power</div>
                  <div className="text-text-primary">{gpu.power_w}W</div>
                </div>
                <div>
                  <div className="text-text-secondary">Util</div>
                  <div className="text-text-primary">{gpu.utilization_percent}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loaded Models */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LOADED MODELS</h3>
        <div className="space-y-3">
          {mockNode.models.map(m => (
            <div key={m.name} className="flex items-center justify-between py-2 border-b border-cyber-border/50 last:border-0">
              <div>
                <div className="font-rajdhani text-sm">{m.name}</div>
                <div className="text-xs text-text-secondary font-mono">{m.vram_required_gb}GB VRAM · {m.total_requests} requests</div>
              </div>
              <Badge status={m.loaded ? 'idle' : 'offline'} label={m.loaded ? 'LOADED' : 'UNLOADED'} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
