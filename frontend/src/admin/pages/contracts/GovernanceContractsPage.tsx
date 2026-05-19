// GovernanceContractsPage.tsx - 治理合约
import { useGovernanceStats, useProposalList } from '../../hooks/useBlockchain'
import StatCard from '../../components/shared/StatCard'
import { useAuthStore } from '@/stores/authStore'
import { Vote, Users, Shield, CheckCircle } from 'lucide-react'
import { useState } from 'react'

export default function GovernanceContractsPage() {
  const { data: stats, isLoading } = useGovernanceStats()
  const { data: proposals, isLoading: proposalsLoading } = useProposalList()
  const address = useAuthStore(s => s.address)
  const [selectedProposal, setSelectedProposal] = useState<number | null>(null)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">治理合约</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="提案总数" value={stats?.proposal_count ?? '-'} icon={Vote} color="primary" loading={isLoading} />
        <StatCard
          title="veToken 总供应"
          value={stats ? `${Number(stats.ve_token_supply).toLocaleString()}` : '-'}
          icon={Shield}
          color="info"
          loading={isLoading}
        />
        <StatCard
          title="委托总量"
          value={stats ? `${Number(stats.total_delegated).toLocaleString()}` : '-'}
          icon={Users}
          color="warning"
          loading={isLoading}
        />
        <StatCard
          title="法定人数"
          value={stats ? `${Number(stats.quorum_votes).toLocaleString()}` : '-'}
          icon={CheckCircle}
          color="success"
          loading={isLoading}
        />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="px-4 py-3 border-b border-border-primary flex items-center justify-between">
          <h3 className="text-text-primary font-rajdhani font-semibold">最新提案</h3>
          <a
            href="https://sepolia.basescan.org/address/0x27475aea1eEba485005B1717a35a7D411d144a1d"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary hover:underline"
          >
            Basescan ↗
          </a>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary bg-bg-tertiary">
              <th className="text-left px-4 py-3 text-text-muted font-normal">ID</th>
              <th className="text-left px-4 py-3 text-text-muted font-normal">描述</th>
              <th className="text-right px-4 py-3 text-text-muted font-normal">赞成</th>
              <th className="text-right px-4 py-3 text-text-muted font-normal">反对</th>
              <th className="text-center px-4 py-3 text-text-muted font-normal">状态</th>
            </tr>
          </thead>
          <tbody>
            {proposalsLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="border-b border-border-primary/50">
                  {[...Array(5)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>)}
                </tr>
              ))
            ) : proposals?.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center text-text-muted py-12">暂无提案数据</td>
              </tr>
            ) : (
              (proposals ?? []).slice(0, 10).map((p) => {
                if (!p) return null
                const forVotes = Number(p.for_votes)
                const againstVotes = Number(p.against_votes)
                const total = forVotes + againstVotes || 1
                return (
                  <tr
                    key={String(p.id)}
                    className="border-b border-border-primary/50 hover:bg-bg-tertiary/30 cursor-pointer"
                    onClick={() => setSelectedProposal(selectedProposal === p.id ? null : p.id)}
                  >
                    <td className="px-4 py-3 font-mono text-text-secondary">#{p.id}</td>
                    <td className="px-4 py-3 text-text-primary">
                      <span className="line-clamp-1">{String(p.description ?? '')}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-success">{forVotes.toLocaleString()}</td>
                    <td className="px-4 py-3 text-right font-mono text-danger">{againstVotes.toLocaleString()}</td>
                    <td className="px-4 py-3 text-center">
                      {p.executed ? (
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-success/10 text-success">已执行</span>
                      ) : (
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs bg-warning/10 text-warning">进行中</span>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>

        {selectedProposal !== null && proposals && (
          <div className="border-t border-border-primary p-4 bg-bg-tertiary/50">
            {(() => {
              const p = (proposals ?? []).find(x => x && x.id === selectedProposal)
              if (!p) return null
              const forVotes = Number(p.for_votes)
              const againstVotes = Number(p.against_votes)
              const total = forVotes + againstVotes || 1
              return (
                <div className="space-y-3">
                  <h4 className="text-text-primary font-semibold">提案 #{p.id}</h4>
                  <p className="text-text-secondary text-sm">{p.description}</p>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-success">赞成: {forVotes.toLocaleString()}</span>
                      <span className="text-text-muted">{((forVotes / total) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                      <div className="h-full bg-success rounded-full" style={{ width: `${(forVotes / total) * 100}%` }} />
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-danger">反对: {againstVotes.toLocaleString()}</span>
                      <span className="text-text-muted">{((againstVotes / total) * 100).toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                      <div className="h-full bg-danger rounded-full" style={{ width: `${(againstVotes / total) * 100}%` }} />
                    </div>
                  </div>
                </div>
              )
            })()}
          </div>
        )}
      </div>
    </div>
  )
}
