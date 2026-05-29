/** AgentsPage - Agent 管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchAgents } from '../../api/adminApi'
import { Bot } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { useState } from 'react'

export default function AgentsPage() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'agents', page, statusFilter],
    queryFn: () => fetchAgents({ page, page_size: 20, status: statusFilter || undefined }),
    refetchInterval: 30000,
  })

  const agents = data?.agents ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        Agent 管理
      </h1>

      {/* 过滤器 */}
      <div className="flex gap-3 items-center">
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="input"
        >
          <option value="">全部状态</option>
          <option value="online">在线</option>
          <option value="busy">忙碌</option>
          <option value="offline">离线</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总 Agent" value={total} icon={Bot} color="primary" loading={isLoading} />
        <StatCard title="在线" value={agents.filter(a => a.status === 'online').length} icon={Bot} color="success" loading={isLoading} />
        <StatCard title="忙碌" value={agents.filter(a => a.status === 'busy').length} icon={Bot} color="warning" loading={isLoading} />
        <StatCard title="离线" value={agents.filter(a => a.status === 'offline').length} icon={Bot} color="danger" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">Agent ID</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">名称</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">类型</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">质押量</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">余额</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">信誉</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-28 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-cyber-dark rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : agents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-gray-500 py-12">暂无 Agent 数据</td>
                </tr>
              ) : (
                agents.map(agent => (
                  <tr key={agent.agent_id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-neon-blue">
                      {agent.agent_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 text-gray-200">
                      {agent.name || '-'}
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs">
                      {agent.agent_type || 'ai_agent'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={agent.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono text-neon-green">
                      {agent.stake.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-400">
                      {agent.balance.toFixed(4)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-mono text-xs ${agent.reputation > 0.7 ? 'text-neon-green' : agent.reputation > 0.4 ? 'text-neon-yellow' : 'text-neon-red'}`}>
                        {(agent.reputation * 100).toFixed(0)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neon-blue/20">
            <span className="text-gray-500 text-sm font-cyber">
              第 {page} / {totalPages} 页，共 {total} 条
            </span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all">
                上一页
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all">
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
