import { Cpu, Zap, DollarSign } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import Badge from '@/components/ui/Badge'
import ProgressBar from '@/components/ui/ProgressBar'
import CyberButton from '@/components/ui/CyberButton'
import { useNavigate } from 'react-router-dom'
import type { GpuInfo } from '@/types/gpu'

export default function NodeDashboardPage() {
  const navigate = useNavigate()

  // Mock data
  const mockGpus: GpuInfo[] = [
    { index: 0, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 38, temperature_c: 72, power_w: 280, utilization_percent: 95, status: 'busy' },
    { index: 1, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 28, temperature_c: 68, power_w: 250, utilization_percent: 70, status: 'busy' },
    { index: 2, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 12, temperature_c: 55, power_w: 180, utilization_percent: 30, status: 'idle' },
    { index: 3, name: 'A100 40GB', vram_total_gb: 40, vram_used_gb: 0, temperature_c: 40, power_w: 50, utilization_percent: 0, status: 'idle' },
  ]

  const mockModels = [
    { name: 'Qwen/Qwen2.5-7B-Instruct', vram_required_gb: 14, total_requests: 156, total_tokens: 45678 },
    { name: 'Qwen/Qwen2.5-14B-Instruct', vram_required_gb: 28, total_requests: 89, total_tokens: 23456 },
  ]

  const totalVramUsed = mockGpus.reduce((s, g) => s + g.vram_used_gb, 0)
  const totalVram = mockGpus.reduce((s, g) => s + g.vram_total_gb, 0)

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
        <div className="font-orbitron text-4xl font-bold neon-text-green mb-1">234.56</div>
        <div className="font-mono text-sm text-neon-green">VIBE</div>
        <div className="text-xs text-text-secondary mt-1">↑ 15% vs yesterday</div>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard label="GPU Utilization" value={`${Math.round((totalVramUsed / totalVram) * 100)}%`} icon={<Cpu size={16} />} accent="blue" />
        <MetricCard label="VRAM Usage" value={`${totalVramUsed}GB / ${totalVram}GB`} icon={<Cpu size={16} />} accent="purple" />
        <MetricCard label="Today's Inference" value={156} icon={<Zap size={16} />} accent="green" trend={12} />
      </div>

      {/* GPU Status */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">GPU STATUS</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {mockGpus.map(gpu => (
            <div key={gpu.index} className="p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div className="flex items-center justify-between mb-2">
                <span className="font-orbitron text-sm text-neon-blue">GPU {gpu.index}: {gpu.name}</span>
                <Badge status={gpu.status} />
              </div>
              <ProgressBar used={gpu.vram_used_gb} total={gpu.vram_total_gb} label={`${gpu.vram_used_gb}GB / ${gpu.vram_total_gb}GB`} />
              <div className="mt-2 grid grid-cols-3 gap-2 text-xs font-mono">
                <div className="text-text-secondary">Temp</div>
                <div className={gpu.temperature_c > 80 ? 'text-neon-red' : 'text-text-primary'}>{gpu.temperature_c}°C</div>
                <div />
                <div className="text-text-secondary">Power</div>
                <div className="text-text-primary">{gpu.power_w}W</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Loaded Models */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LOADED MODELS</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {mockModels.map(m => (
            <div key={m.name} className="p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div className="flex items-center justify-between mb-2">
                <span className="font-rajdhani text-sm text-text-primary">{m.name}</span>
                <CyberButton variant="ghost" size="sm">Unload</CyberButton>
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
            <div className="text-xs text-text-secondary mt-1 font-mono">192.168.1.1:8000</div>
          </div>
          <div className="text-right">
            <div className="text-xs text-text-secondary">Last Heartbeat</div>
            <div className="text-xs font-mono text-text-primary">5 seconds ago</div>
          </div>
        </div>
      </div>
    </div>
  )
}
