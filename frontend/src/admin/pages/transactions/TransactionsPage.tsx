/** TransactionsPage - 交易流水 */
import { useQuery } from '@tanstack/react-query'
import { fetchTransactions } from '../../api/adminApi'
import { ArrowLeftRight } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { useState } from 'react'

function shortAddr(addr: string): string {
  if (!addr || addr.length < 12) return addr || '-'
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

export default function TransactionsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'transactions', page],
    queryFn: () => fetchTransactions({ page, page_size: 20 }),
    refetchInterval: 60000,
  })

  const transactions = data?.transactions ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  const totalVolume = transactions.reduce((sum, t) => sum + t.amount, 0)
  const completedCount = transactions.filter(t => t.status === 'completed').length

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">交易流水</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总交易数" value={total} icon={ArrowLeftRight} color="primary" loading={isLoading} />
        <StatCard title="本页总额" value={totalVolume.toFixed(2)} icon={ArrowLeftRight} color="info" loading={isLoading} />
        <StatCard title="本页成功" value={completedCount} icon={ArrowLeftRight} color="success" loading={isLoading} />
        <StatCard title="总页数" value={totalPages} icon={ArrowLeftRight} color="info" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">交易ID</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">类型</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">金额</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">手续费</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">发送方</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">接收方</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-text-muted py-12">暂无交易数据</td>
                </tr>
              ) : (
                transactions.map(tx => (
                  <tr key={tx.tx_id} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {shortAddr(tx.tx_id)}
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      {tx.type || 'unknown'}
                    </td>
                    <td className={`px-4 py-3 font-mono ${tx.amount >= 0 ? 'text-success' : 'text-danger'}`}>
                      {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-secondary text-xs">
                      {tx.fee.toFixed(6)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tx.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {shortAddr(tx.from_address)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {shortAddr(tx.to_address)}
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
