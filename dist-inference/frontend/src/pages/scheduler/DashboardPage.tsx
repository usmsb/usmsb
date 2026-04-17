import { Cpu, Zap, FileText, DollarSign } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import Badge from '@/components/ui/Badge'
import AreaTrendChart from '@/components/charts/AreaTrendChart'
import { useGpuPool } from '@/hooks/useGpuPool'
import { useRequests } from '@/hooks/useRequests'
import { useRevenueStats } from '@/hooks/useRevenue'
import { formatNumber, formatVibe, formatTime } from '@/lib/utils'
import { useNavigate } from 'react-router-dom'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: nodes = [] } = useGpuPool()
  const { data: requestsData } = useRequests({ page_size: 5 })
  const { data: revenue } = useRevenueStats()

  const activeNodes = nodes.filter(n => n.status !== 'offline').length
  const totalGpus = nodes.reduce((sum, n) => sum + n.gpu_count, 0)
  const totalRequests = requestsData?.data?.length || 0
  const recentRequests = (requestsData?.data || []).slice(0, 5)

  // Mock trend data for demo
  const trendData = Array.from({ length: 30 }, (_, i) => ({
    date: `Day ${i + 1}`,
    value: Math.floor(Math.random() * 1000) + 500,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-orbitron text-xl font-bold neon-text-blue">SYSTEM OVERVIEW</h1>
          <p className="text-text-secondary text-sm font-rajdhani mt-1">Real-time distributed inference network</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="live-dot" />
          <span className="text-xs font-mono text-neon-green">LIVE</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Nodes"
          value={activeNodes}
          icon={<Cpu size={16} />}
          accent="blue"
          trend={12}
        />
        <MetricCard
          label="Total GPU"
          value={totalGpus}
          subValue={`${nodes.reduce((s, n) => s + n.gpus.reduce((gs, g) => gs + g.vram_used_gb, 0), 0)} GB used`}
          icon={<Zap size={16} />}
          accent="purple"
        />
        <MetricCard
          label="Today's Inference"
          value={formatNumber(1234)}
          icon={<FileText size={16} />}
          accent="green"
          trend={15}
        />
        <MetricCard
          label="Today's Revenue"
          value={formatVibe(8234.56)}
          subValue="VIBE"
          icon={<DollarSign size={16} />}
          accent="blue"
          trend={8}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">GPU UTILIZATION (REAL-TIME)</h3>
          <AreaTrendChart data={trendData} dataKey="value" color="#00f5ff" height={200} />
        </div>
        <div className="cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LIVE INFERENCE QUEUE</h3>
          <div className="space-y-2">
            {recentRequests.length === 0 ? (
              <p className="text-text-secondary text-sm text-center py-8">No active requests</p>
            ) : (
              recentRequests.map(req => (
                <div
                  key={req.request_id}
                  className="flex items-center justify-between py-2 border-b border-cyber-border/50 last:border-0 cursor-pointer hover:bg-neon-blue/5 px-2 rounded"
                  onClick={() => navigate(`/requests/${req.request_id}`)}
                >
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs text-text-secondary">{req.request_id.slice(0, 8)}</span>
                    <span className="text-sm font-rajdhani">{req.model_name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge status={req.status} dot />
                    <span className="text-xs font-mono text-text-secondary">{formatTime(req.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Quick Node Status */}
      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">ACTIVE NODES</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {nodes.slice(0, 8).map(node => (
            <div
              key={node.node_id}
              className="p-3 bg-black/20 rounded-lg border border-cyber-border hover:border-neon-blue/40 transition-colors cursor-pointer"
              onClick={() => navigate(`/nodes/${node.node_id}`)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs text-neon-blue">{node.node_id}</span>
                <Badge status={node.status} />
              </div>
              <div className="text-xs font-rajdhani text-text-secondary">
                {node.gpu_count}x GPU · {node.models.length} models
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
