import { Radio } from 'lucide-react'
import { useGpuPool } from '@/hooks/useGpuPool'
import { useRequests } from '@/hooks/useRequests'
import Badge from '@/components/ui/Badge'
import ProgressBar from '@/components/ui/ProgressBar'
import MetricCard from '@/components/ui/MetricCard'

export default function MonitorPage() {
  const { data: nodes = [] } = useGpuPool()
  const { data: requestsData } = useRequests({ page_size: 10 })

  // Mock event log
  const events = [
    { time: new Date().toISOString(), type: 'info', msg: 'GPU pool updated' },
    { time: new Date(Date.now() - 5000).toISOString(), type: 'success', msg: 'node_002 heartbeat received' },
    { time: new Date(Date.now() - 15000).toISOString(), type: 'warning', msg: 'node_003 temperature 85°C' },
    { time: new Date(Date.now() - 30000).toISOString(), type: 'success', msg: 'Request req_abc123 completed' },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-orbitron text-xl font-bold neon-text-blue flex items-center gap-2">
          <Radio size={20} className="text-neon-green animate-pulse" />
          REAL-TIME MONITOR
        </h1>
        <div className="flex items-center gap-2">
          <span className="live-dot" />
          <span className="text-xs font-mono text-neon-green">LIVE</span>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Active Nodes" value={nodes.filter(n => n.status !== 'offline').length} accent="green" />
        <MetricCard label="Total GPUs" value={nodes.reduce((s, n) => s + n.gpu_count, 0)} accent="blue" />
        <MetricCard label="Queue" value={requestsData?.data?.filter(r => r.status === 'queued').length || 0} accent="purple" />
        <MetricCard label="Running" value={requestsData?.data?.filter(r => r.status === 'running').length || 0} accent="blue" />
      </div>

      {/* GPU Status Grid */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">GPU STATUS GRID</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {nodes.flatMap(node =>
            node.gpus.map(gpu => (
              <div key={`${node.node_id}-gpu-${gpu.index}`} className="p-3 bg-black/20 rounded-lg border border-cyber-border">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-xs text-neon-blue">{node.node_id} / GPU {gpu.index}</span>
                  <Badge status={gpu.status} />
                </div>
                <ProgressBar used={gpu.vram_used_gb} total={gpu.vram_total_gb} showLabel={false} height="sm" />
                <div className="mt-1 text-xs font-mono text-text-secondary">{gpu.utilization_percent}%</div>
              </div>
            ))
          )}
          {nodes.length === 0 && Array.from({ length: 8 }, (_, i) => (
            <div key={`empty-${i}`} className="p-3 bg-black/20 rounded-lg border border-cyber-border opacity-40">
              <span className="font-mono text-xs text-text-secondary">No data</span>
            </div>
          ))}
        </div>
      </div>

      {/* Event Log */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">EVENT LOG</h3>
        <div className="space-y-2 font-mono text-xs">
          {events.map((e, i) => (
            <div key={i} className="flex gap-3 py-1 border-b border-cyber-border/30 last:border-0">
              <span className="text-text-secondary shrink-0">{new Date(e.time).toLocaleTimeString()}</span>
              <span className={e.type === 'success' ? 'text-neon-green' : e.type === 'warning' ? 'text-neon-yellow' : 'text-neon-blue'}>●</span>
              <span className="text-text-primary">{e.msg}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
