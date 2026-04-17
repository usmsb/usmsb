import { Boxes, Download, Upload } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import ProgressBar from '@/components/ui/ProgressBar'
import CyberButton from '@/components/ui/CyberButton'
import Badge from '@/components/ui/Badge'

export default function NodeModelsPage() {
  // Mock
  const totalVram = 200
  const usedVram = 60
  const availableVram = totalVram - usedVram

  const loadedModels = [
    { id: '1', name: 'Qwen/Qwen2.5-7B-Instruct', vram_required_gb: 14, loaded_at: new Date().toISOString(), total_requests: 156 },
    { id: '2', name: 'Qwen/Qwen2.5-14B-Instruct', vram_required_gb: 28, loaded_at: new Date().toISOString(), total_requests: 89 },
  ]

  const availableModels = [
    { id: '3', name: 'Qwen/Qwen2.5-72B-Instruct', vram_required_gb: 160, can_load: false },
    { id: '4', name: 'THUDM/CogVideoX-5b', vram_required_gb: 48, can_load: false },
    { id: '5', name: 'MiniCPM-2B', vram_required_gb: 6, can_load: true },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">MODEL MANAGEMENT</h1>

      <div className="cyber-card p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-rajdhani text-text-secondary uppercase tracking-widest">GPU VRAM</span>
          <span className="font-mono text-xs text-neon-blue">{usedVram}GB / {totalVram}GB ({Math.round((usedVram/totalVram)*100)}%)</span>
        </div>
        <ProgressBar used={usedVram} total={totalVram} showLabel={false} height="md" />
        <div className="mt-2 text-xs text-text-secondary font-mono">Available: {availableVram}GB</div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LOADED MODELS</h3>
        <div className="space-y-3">
          {loadedModels.map(m => (
            <div key={m.id} className="flex items-center justify-between p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div>
                <div className="font-rajdhani text-sm text-text-primary">{m.name}</div>
                <div className="text-xs text-text-secondary font-mono">VRAM: {m.vram_required_gb}GB · Requests: {m.total_requests}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge status="idle" label="LOADED" />
                <CyberButton variant="ghost" size="sm">
                  <Upload size={12} />
                  Unload
                </CyberButton>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">AVAILABLE MODELS</h3>
        <div className="space-y-3">
          {availableModels.map(m => (
            <div key={m.id} className="flex items-center justify-between p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div>
                <div className="font-rajdhani text-sm text-text-primary">{m.name}</div>
                <div className="text-xs text-text-secondary font-mono">Requires: {m.vram_required_gb}GB</div>
              </div>
              {m.can_load ? (
                <CyberButton variant="primary" size="sm">
                  <Download size={12} />
                  Load
                </CyberButton>
              ) : (
                <span className="text-xs text-neon-yellow">⚠ Insufficient VRAM</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
