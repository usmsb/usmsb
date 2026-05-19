/** TransactionsPage - 交易流水 */
import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '../../api/adminApi'
import { ArrowLeftRight } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'

export default function TransactionsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'transactions'],
    queryFn: () => fetchTransactions({ pageSize: 50 }),
    refetchInterval: 60000,
  })

  const txs = data?.transactions ?? []
  const summary = data?.summary

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">交易流水</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总交易数" value={data?.total ?? 0} icon={ArrowLeftRight} color="primary" loading={isLoading} />
        <StatCard title="今日笔数" value={summary?.todayCount ?? 0} icon={ArrowLeftRight} color="info" loading={isLoading} />
        <StatCard title="今日金额" value={summary?.todayVolume ?? '0'} icon={ArrowLeftRight} color="success" suffix="VIBE" loading={isLoading} />
        <StatCard title="成功率" value={summary?.successRate ?? 0} suffix="%" color="success" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-bg-tertiary border-b border-border-primary">
              <tr>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">时间</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">From</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">To</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">金额</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">类型</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">状态</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {isLoading ? (
                <tr><td colSpan={6} className="py-8 text-center text-text-muted">加载中...</td></tr>
              ) : txs.length === 0 ? (
                <tr><td colSpan={6} className="py-8 text-center text-text-muted text-sm">暂无交易数据</td></tr>
              ) : (
                txs.map(tx => (
                  <tr key={tx.id} className="hover:bg-bg-tertiary/50">
                    <td className="py-3 px-4 text-text-muted text-xs">
                      {new Date(tx.createdAt * 1000).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="py-3 px-4 text-text-secondary text-xs font-mono">{tx.buyerId?.slice(0, 8)}...</td>
                    <td className="py-3 px-4 text-text-secondary text-xs font-mono">{tx.sellerId?.slice(0, 8)}...</td>
                    <td className="py-3 px-4">
                      <span className={tx.buyerId ? 'text-danger' : 'text-success'}>
                        {tx.buyerId ? '-' : '+'}{Number(tx.amount).toLocaleString()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-text-secondary text-xs">{tx.transactionType}</td>
                    <td className="py-3 px-4"><StatusBadge status={tx.status} size="sm" /></td>
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
