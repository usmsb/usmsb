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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        节点管理
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总节点" value={total} icon={Server} color="primary" loading={isLoading} />
        <StatCard title="在线" value={online} icon={Server} color="success" loading={isLoading} />
        <StatCard title="离线" value={offline} icon={Server} color="danger" loading={isLoading} />
        <StatCard title="在线率" value={total > 0 ? ((online / total) * 100).toFixed(1) + '%' : '0%'} icon={Server} color="info" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">节点名称</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">Agent数</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">CPU</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">内存</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">版本</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">最后活跃</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(3)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-28 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : nodes.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-gray-500 py-12">暂无节点数据</td>
                </tr>
              ) : (
                nodes.map(node => (
                  <tr key={node.node_id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
                    <td className="px-4 py-3 text-gray-200 font-medium">
                      {node.name || node.node_id.slice(0, 8)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={node.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 text-neon-blue">
                      {node.agent_count}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ProgressBar percent={node.cpu_percent} />
                        <span className={`text-xs font-mono ${node.cpu_percent > 80 ? 'text-neon-red' : 'text-neon-green'}`}>
                          {node.cpu_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <ProgressBar percent={node.memory_percent} />
                        <span className={`text-xs font-mono ${node.memory_percent > 80 ? 'text-neon-red' : 'text-neon-green'}`}>
                          {node.memory_percent.toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {node.version || '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
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
