/** NodesPage - 节点管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchNodes } from '../../api/adminApi'
import { Server } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { ProgressBar } from '../../components/shared/ProgressBar'

function timeAgo(ts: number): string {
  const s = Math.floor(Date.now() / 1000 - ts)
  if (s < 60) return `${s}s前`
  if (s < 3600) return `${Math.floor(s / 60)}m前`
  if (s < 86400) return `${Math.floor(s / 3600)}h前`
  return `${Math.floor(s / 86400)}d前`
}

export default function NodesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'nodes'],
    queryFn: fetchNodes,
    refetchInterval: 30000,
  })

  const nodes = data?.nodes ?? []
  const online = data?.online ?? 0
  const offline = data?.offline ?? 0
  const total = data?.total ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">节点管理</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总节点" value={total} icon={Server} color="primary" loading={isLoading} />
        <StatCard title="在线" value={online} icon={Server} color="success" loading={isLoading} />
        <StatCard title="离线" value={offline} icon={Server} color="danger" loading={isLoading} />
        <StatCard title="在线率" value={total > 0 ? ((online / total) * 100).toFixed(1) + '%' : '0%'} icon={Server} color="info" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">节点名称</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">Agent数</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">CPU</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">内存</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">版本</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">最后活跃</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(3)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-28 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : nodes.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-text-muted py-12">暂无节点数据</td>
                </tr>
              ) : (
                nodes.map(node => (
                  <tr key={node.node_id} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 text-text-primary font-medium">
                      {node.name || node.node_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={node.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      {node.agent_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ProgressBar percent={node.cpu_percent} />
                        <span className={`text-xs font-mono ${node.cpu_percent > 80 ? 'text-danger' : 'text-text-secondary'}`}>
                          {node.cpu_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ProgressBar percent={node.memory_percent} />
                        <span className={`text-xs font-mono ${node.memory_percent > 80 ? 'text-danger' : 'text-text-secondary'}`}>
                          {node.memory_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs">
                      {node.version || '-'}
                    </td>
                    <td className="px-4 py-3 text-text-muted text-xs">
                      {node.last_heartbeat ? timeAgo(node.last_heartbeat) : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
