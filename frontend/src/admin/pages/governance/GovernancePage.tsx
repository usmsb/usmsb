/** GovernancePage - 治理投票 */
import { useQuery } from '@tanstack/react-query'
import { fetchProposals } from '../../api/adminApi'
import { Vote } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'

export default function GovernancePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'governance', 'proposals'],
    queryFn: () => fetchProposals({ pageSize: 50 }),
    refetchInterval: 300000,
  })

  const proposals = data?.proposals ?? []
  const activeCount = proposals.filter(p => p.status === 'active').length

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">治理投票</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="提案总数" value={data?.total ?? 0} icon={Vote} color="primary" loading={isLoading} />
        <StatCard title="进行中" value={activeCount} icon={Vote} color="success" loading={isLoading} />
        <StatCard title="已通过" value={proposals.filter(p => p.status === 'passed').length} icon={Vote} color="info" loading={isLoading} />
        <StatCard title="已否决" value={proposals.filter(p => p.status === 'rejected').length} icon={Vote} color="danger" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-bg-tertiary border-b border-border-primary">
              <tr>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">ID</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">标题</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">类型</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">状态</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">赞成/反对</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {isLoading ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted">加载中...</td></tr>
              ) : proposals.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted text-sm">暂无提案数据</td></tr>
              ) : (
                proposals.map(p => (
                  <tr key={p.id} className="hover:bg-bg-tertiary/50">
                    <td className="py-3 px-4 text-text-muted text-sm font-mono">#{p.id}</td>
                    <td className="py-3 px-4 text-text-primary text-sm font-medium">{p.title}</td>
                    <td className="py-3 px-4 text-text-secondary text-xs">{p.proposalType}</td>
                    <td className="py-3 px-4"><StatusBadge status={p.status} size="sm" /></td>
                    <td className="py-3 px-4">
                      <span className="text-success text-xs">{Number(p.votesFor).toLocaleString()}</span>
                      {' / '}
                      <span className="text-danger text-xs">{Number(p.votesAgainst).toLocaleString()}</span>
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
