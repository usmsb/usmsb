/**
 * AgentsPage - Agent 管理
 */
import { useQuery } from '@tanstack/react-query'
import { fetchAgents } from '../../api/adminApi'
import { Bot } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { Link } from 'react-router-dom'

export default function AgentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'agents'],
    queryFn: () => fetchAgents({ pageSize: 100 }),
    refetchInterval: 30000,
  })

  const agents = data?.agents ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary font-rajdhani">Agent 管理</h1>
          <p className="text-text-muted text-sm mt-1">全局 Agent 列表及管理</p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总数" value={data?.total ?? 0} icon={Bot} color="primary" loading={isLoading} />
        <StatCard title="在线" value={agents.filter(a => a.status === 'online').length} icon={Bot} color="success" loading={isLoading} />
        <StatCard title="忙碌" value={agents.filter(a => a.status === 'busy').length} icon={Bot} color="warning" loading={isLoading} />
        <StatCard title="离线" value={agents.filter(a => a.status === 'offline').length} icon={Bot} color="danger" loading={isLoading} />
      </div>

      {/* Agent 列表 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-bg-tertiary border-b border-border-primary">
              <tr>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">Agent</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">类型</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">状态</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">Stake</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">Reputation</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="hover:bg-bg-tertiary/50">
                    <td className="py-3 px-4"><div className="h-4 w-32 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="py-3 px-4"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="py-3 px-4"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="py-3 px-4"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="py-3 px-4"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="py-3 px-4"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : agents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-text-muted text-sm">暂无 Agent 数据</td>
                </tr>
              ) : (
                agents.map(agent => (
                  <tr key={agent.agentId} className="hover:bg-bg-tertiary/50 transition-colors">
                    <td className="py-3 px-4">
                      <div>
                        <p className="text-text-primary text-sm font-medium">{agent.name || agent.agentId.slice(0, 12)}</p>
                        <p className="text-text-muted text-xs font-mono">{agent.agentId.slice(0, 16)}...</p>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={agent.agentType} size="sm" />
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={agent.status} size="sm" />
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-text-primary text-sm font-mono">
                        {Number(agent.stake).toLocaleString()} VIBE
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-text-primary text-sm">⭐ {agent.reputation.toFixed(1)}</span>
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/admin/agents/${agent.agentId}`}
                        className="text-primary text-sm hover:underline"
                      >
                        详情 →
                      </Link>
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
