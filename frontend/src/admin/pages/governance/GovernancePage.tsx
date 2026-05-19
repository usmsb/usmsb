/** GovernancePage - 治理投票 */
import { useQuery } from '@tanstack/react-query'
import { fetchGovernance } from '../../api/adminApi'
import { Target, ThumbsUp, ThumbsDown } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'

export default function GovernancePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'governance'],
    queryFn: fetchGovernance,
    refetchInterval: 60000,
  })

  const proposals = data?.proposals ?? []
  const activeProposals = data?.active_proposals ?? 0
  const totalVotes = data?.total_votes ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">治理投票</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard title="活跃提案" value={activeProposals} icon={Target} color="warning" loading={isLoading} />
        <StatCard title="总提案" value={proposals.length} icon={Target} color="primary" loading={isLoading} />
        <StatCard title="总投票数" value={totalVotes} icon={ThumbsUp} color="info" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">提案ID</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">赞成</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">反对</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(3)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : proposals.length === 0 ? (
                <tr>
                  <td colSpan={4} className="text-center text-text-muted py-12">暂无提案数据</td>
                </tr>
              ) : (
                proposals.map((p: Record<string, unknown>) => (
                  <tr key={p.proposal_id as string || p.id as string} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {(p.proposal_id as string || p.id as string || '').slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={(p.status as string) || 'active'} size="sm" />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-success font-mono">{(p.votes_for as number || 0).toLocaleString()}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-danger font-mono">{(p.votes_against as number || 0).toLocaleString()}</span>
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
