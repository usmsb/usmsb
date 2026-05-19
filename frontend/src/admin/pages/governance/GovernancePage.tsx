/** GovernancePage - 治理投票（增强版） */
import { useQuery } from '@tanstack/react-query'
import { fetchGovernance } from '../../api/adminApi'
import type { GovernanceData } from '../../api/adminApi'
import { useGovernanceStats, useProposalList } from '../../hooks/useBlockchain'
import { Target, ThumbsUp, Vote } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import ProposalsTable from './components/ProposalsTable'

export default function GovernancePage() {
  const { data, isLoading } = useQuery<GovernanceData>({
    queryKey: ['admin', 'governance'],
    queryFn: fetchGovernance,
    refetchInterval: 60000,
  })

  // 链上提案数据
  const { data: chainProposals, isLoading: chainLoading } = useProposalList()
  const { data: chainStats } = useGovernanceStats()

  const proposals = data?.proposals ?? []
  const activeProposals = data?.active_proposals ?? 0
  const totalVotes = data?.total_votes ?? 0
  const chainTotal = chainStats?.proposal_count ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">治理投票</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="活跃提案" value={activeProposals} icon={Target} color="warning" loading={isLoading} />
        <StatCard title="总提案（链上）" value={chainTotal} icon={Target} color="primary" loading={chainLoading} />
        <StatCard title="总投票数" value={totalVotes} icon={ThumbsUp} color="info" loading={isLoading} />
        <StatCard
          title="VE Token 供应"
          value={chainStats ? `${Number(chainStats.ve_token_supply).toLocaleString()}` : '-'}
          icon={Vote}
          color="success"
          loading={chainLoading}
        />
      </div>

      {/* 提案列表（链上数据，可展开详情） */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="px-4 py-3 border-b border-border-primary bg-bg-tertiary flex items-center justify-between">
          <h3 className="text-text-primary font-rajdhani font-semibold">链上提案</h3>
          <a
            href="https://sepolia.basescan.org/address/0x27475aea1eEba485005B1717a35a7D411d144a1d"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline"
          >
            Basescan ↗
          </a>
        </div>
        <div className="p-4">
          {chainLoading ? (
            <div className="space-y-3">
              {[...Array(5)].map((_, i) => <div key={i} className="h-16 bg-bg-tertiary rounded-lg animate-pulse" />)}
            </div>
          ) : chainProposals && chainProposals.length > 0 ? (
            <ProposalsTable
              proposals={(chainProposals ?? []).map((p: any) => ({
                id: p.id as number,
                description: p.description as string || '',
                proposer: p.proposer as string || '',
                for_votes: Number(p.for_votes),
                against_votes: Number(p.against_votes),
                deadline: p.deadline as number,
                executed: Boolean(p.executed),
              }))}
            />
          ) : (
            <div className="text-center text-text-muted py-12">
              {proposals.length > 0 ? '链上暂无提案数据，使用数据库记录' : '暂无提案数据'}
            </div>
          )}
        </div>
      </div>

      {/* 数据库记录列表（备用） */}
      {proposals.length > 0 && (
        <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-bg-tertiary">
            <h3 className="text-text-primary font-rajdhani font-semibold">数据库提案记录</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-primary bg-bg-tertiary">
                  <th className="text-left px-4 py-3 text-text-muted font-normal">提案ID</th>
                  <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
                  <th className="text-right px-4 py-3 text-text-muted font-normal">赞成</th>
                  <th className="text-right px-4 py-3 text-text-muted font-normal">反对</th>
                </tr>
              </thead>
              <tbody>
                {proposals.map((p: Record<string, unknown>) => (
                  <tr key={p.proposal_id as string || p.id as string} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {(p.proposal_id as string || p.id as string || '').slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary">
                        {(p.status as string) || 'active'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-success">
                      {(p.votes_for as number || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-danger">
                      {(p.votes_against as number || 0).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
