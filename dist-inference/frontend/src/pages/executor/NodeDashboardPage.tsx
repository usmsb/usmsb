import { useState, useEffect } from 'react'
import { Cpu, Zap } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import Badge from '@/components/ui/Badge'
import ProgressBar from '@/components/ui/ProgressBar'
import CyberButton from '@/components/ui/CyberButton'
import { useNavigate } from 'react-router-dom'
import { fetchNodeStatus, fetchNodeEarnings, unloadModel } from '@/lib/api'
import toast from 'react-hot-toast'
import type { GpuInfo } from '@/types/gpu'

interface NodeStatusData {
  node_id: string
  status: string
  wallet_address: string
  uptime_seconds: number
  version: string
  gpu_info: {
    gpu_count: number
    gpus: Array<{
      id: number
      name: string
      vram_gb: number
      used_vram_gb: number
      utilization: number
    }>
  }
  loaded_models: string[]
  gpu_threshold: number
}

interface EarningsData {
  total_revenue_vibe: number
  total_requests: number
}

export default function NodeDashboardPage() {
  const navigate = useNavigate()
  const [nodeStatus, setNodeStatus] = useState<NodeStatusData | null>(null)
  const [earnings, setEarnings] = useState<EarningsData | null>(null)
  const [unloading, setUnloading] = useState<string | null>(null)

  useEffect(() => {
    fetchNodeStatus()
      .then((data: Record<string, unknown>) => setNodeStatus(data as unknown as NodeStatusData))
      .catch(() => {})
    fetchNodeEarnings({ days: 1 })
      .then((data: Record<string, unknown>) => setEarnings(data as unknown as EarningsData))
      .catch(() => {})
  }, [])

  const handleUnload = async (modelId: string) => {
    setUnloading(modelId)
    try {
      await unloadModel(modelId)
      toast.success(`${modelId} unload requested`)
      fetchNodeStatus()
        .then((data: Record<string, unknown>) => setNodeStatus(data as unknown as NodeStatusData))
        .catch(() => {})
    } catch (e) {
      toast.error(String(e))
    } finally {
      setUnloading(null)
    }
  }

  const gpus: GpuInfo[] = nodeStatus?.gpu_info?.gpus?.map((g) => ({
    index: g.id,
    name: g.name,
    vram_total_gb: g.vram_gb,
    vram_used_gb: g.used_vram_gb,
    temperature_c: 0,
    power_w: 0,
    utilization_percent: Math.round(g.utilization * 100),
    status: g.utilization > 0.5 ? 'busy' : 'idle',
  })) || [
    { index: 0, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 38, temperature_c: 72, power_w: 280, utilization_percent: 95, status: 'busy' },
    { index: 1, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 28, temperature_c: 68, power_w: 250, utilization_percent: 70, status: 'busy' },
    { index: 2, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 12, temperature_c: 55, power_w: 180, utilization_percent: 30, status: 'idle' },
    { index: 3, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 0, temperature_c: 40, power_w: 50, utilization_percent: 0, status: 'idle' },
  ]

  const loadedModels = (nodeStatus?.loaded_models || ['Qwen/Qwen2.5-7B-Instruct', 'Qwen/Qwen2.5-14B-Instruct']).map(name => ({
    name,
    vram_required_gb: name.includes('72B') ? 160 : name.includes('14B') ? 28 : 14,
    total_requests: 0,
  }))

  const totalVramUsed = gpus.reduce((s, g) => s + g.vram_used_gb, 0)
  const totalVram = gpus.reduce((s, g) => s + g.vram_total_gb, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="font-orbitron text-xl font-bold neon-text-blue">NODE DASHBOARD</h1>
        <div className="flex items-center gap-2">
          <span className="live-dot" />
          <span className="text-xs font-mono text-neon-green">LIVE</span>
        </div>
      </div>

      {/* Today's Earnings */}
      <div className="cyber-card p-6 text-center">
        <div className="text-xs font-rajdhani text-text-secondary uppercase tracking-widest mb-2">TODAY'S EARNINGS</div>
        <div className="font-orbitron text-4xl font-bold neon-text-green mb-1">
          {earnings?.total_revenue_vibe?.toFixed(2) || '0.00'}
        </div>
        <div className="font-mono text-sm text-neon-green">VIBE</div>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="GPU Utilization"
          value={`${Math.round((totalVramUsed / totalVram) * 100)}%`}
          icon={<Cpu size={16} />}
          accent="blue"
        />
        <MetricCard
          label="VRAM Usage"
          value={`${totalVramUsed}GB / ${totalVram}GB`}
          icon={<Cpu size={16} />}
          accent="purple"
        />
        <MetricCard
          label="Today's Inference"
          value={earnings?.total_requests || 0}
          icon={<Zap size={16} />}
          accent="green"
        />
      </div>

      {/* GPU Status */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">GPU STATUS</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {gpus.map(gpu => (
            <div key={gpu.index} className="p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div className="flex items-center justify-between mb-2">
                <span className="font-orbitron text-sm text-neon-blue">GPU {gpu.index}: {gpu.name}</span>
                <Badge status={gpu.status} />
              </div>
              <ProgressBar used={gpu.vram_used_gb} total={gpu.vram_total_gb} label={`${gpu.vram_used_gb}GB / ${gpu.vram_total_gb}GB`} />
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="text-text-secondary">Util</div>
                <div className="text-text-primary">{gpu.utilization_percent}%</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loaded Models */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LOADED MODELS</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {loadedModels.map(m => (
            <div key={m.name} className="p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div className="flex items-center justify-between mb-2">
                <span className="font-rajdhani text-sm text-text-primary">{m.name}</span>
                <CyberButton
                  variant="ghost"
                  size="sm"
                  loading={unloading === m.name}
                  onClick={() => handleUnload(m.name)}
                >
                  Unload
                </CyberButton>
              </div>
              <div className="text-xs text-text-secondary font-mono">VRAM: {m.vram_required_gb}GB · Requests: {m.total_requests}</div>
            </div>
          ))}
          <CyberButton variant="secondary" size="sm" onClick={() => navigate('/node/models')}>
            + Load Model
          </CyberButton>
        </div>
      </div>

      {/* Scheduler Connection */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-3 tracking-widest">SCHEDULER CONNECTION</h3>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-neon-green" />
              <span className="font-rajdhani text-sm text-neon-green">Connected</span>
            </div>
            <div className="text-xs text-text-secondary mt-1 font-mono">
              {nodeStatus?.node_id || 'Node ID: unknown'}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-text-secondary">Uptime</div>
            <div className="text-xs font-mono text-text-primary">
              {nodeStatus?.uptime_seconds
                ? `${Math.floor(nodeStatus.uptime_seconds / 3600)}h ${Math.floor((nodeStatus.uptime_seconds % 3600) / 60)}m`
                : '--'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
