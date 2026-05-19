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
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">Agent 管理</h1>

      {/* 过滤器 */}
      <div className="flex gap-3 items-center">
        <select
          value={statusFilter}
          onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
          className="bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-3 py-2 text-sm outline-none"
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

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">Agent ID</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">名称</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">类型</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">质押量</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">余额</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">信誉</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-28 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : agents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-text-muted py-12">暂无 Agent 数据</td>
                </tr>
              ) : (
                agents.map(agent => (
                  <tr key={agent.agent_id} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {agent.agent_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      {agent.name || '-'}
                    </td>
                    <td className="px-4 py-3 text-text-secondary text-xs">
                      {agent.agent_type || 'ai_agent'}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={agent.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono text-text-primary">
                      {agent.stake.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-secondary">
                      {agent.balance.toFixed(4)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-mono text-xs ${agent.reputation > 0.7 ? 'text-success' : agent.reputation > 0.4 ? 'text-warning' : 'text-danger'}`}>
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
          <div className="flex items-center justify-between px-4 py-3 border-t border-border-primary">
            <span className="text-text-muted text-sm">
              第 {page} / {totalPages} 页，共 {total} 条
            </span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-50 text-sm">
                上一页
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-50 text-sm">
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
