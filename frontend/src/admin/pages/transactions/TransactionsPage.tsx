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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        交易流水
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总交易数" value={total} icon={ArrowLeftRight} color="primary" loading={isLoading} />
        <StatCard title="本页总额" value={totalVolume.toFixed(2)} icon={ArrowLeftRight} color="info" loading={isLoading} />
        <StatCard title="本页成功" value={completedCount} icon={ArrowLeftRight} color="success" loading={isLoading} />
        <StatCard title="总页数" value={totalPages} icon={ArrowLeftRight} color="info" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">交易ID</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">类型</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">金额</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">手续费</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">发送方</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">接收方</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-gray-500 py-12">暂无交易数据</td>
                </tr>
              ) : (
                transactions.map(tx => (
                  <tr key={tx.tx_id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-neon-blue">
                      {shortAddr(tx.tx_id)}
                    </td>
                    <td className="px-4 py-3 text-gray-200">
                      {tx.type || 'unknown'}
                    </td>
                    <td className={`px-4 py-3 font-mono ${tx.amount >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                      {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(4)}
                    </td>
                    <td className="px-4 py-3 font-mono text-gray-500 text-xs">
                      {tx.fee.toFixed(6)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={tx.status} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {shortAddr(tx.from_address)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {shortAddr(tx.to_address)}
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
