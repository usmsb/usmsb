/**
 * RecentTransactionsTable - 最新交易表格
 */
import StatusBadge from '../../../components/shared/StatusBadge'
import type { Transaction } from '../../../api/adminApi'

interface RecentTransactionsTableProps {
  transactions: Transaction[]
  loading?: boolean
}

function formatTime(timestamp: number): string {
  const d = new Date(timestamp * 1000)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatAmount(amount: string | number): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toFixed(2)
}

function shortAddress(addr: string): string {
  if (!addr) return '-'
  if (addr.length < 16) return addr
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

const typeColors: Record<string, string> = {
  payment: 'text-info',
  stake: 'text-warning',
  reward: 'text-success',
  refund: 'text-muted',
  governance: 'text-primary',
}

export default function RecentTransactionsTable({ transactions, loading }: RecentTransactionsTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-10 bg-bg-tertiary rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted text-sm">
        暂无交易记录
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border-primary">
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-3">时间</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-3">From</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-3">To</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-3">金额</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-3">类型</th>
            <th className="text-left text-text-muted text-xs font-medium py-2">状态</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-primary">
          {transactions.slice(0, 8).map(tx => (
            <tr key={tx.id} className="hover:bg-bg-tertiary/50 transition-colors">
              <td className="py-2.5 pr-3">
                <span className="text-text-muted text-xs whitespace-nowrap">
                  {formatTime(tx.createdAt)}
                </span>
              </td>
              <td className="py-2.5 pr-3">
                <span className="text-text-secondary text-xs font-mono">
                  {shortAddress(tx.buyerId)}
                </span>
              </td>
              <td className="py-2.5 pr-3">
                <span className="text-text-secondary text-xs font-mono">
                  {shortAddress(tx.sellerId)}
                </span>
              </td>
              <td className="py-2.5 pr-3">
                <span className={tx.buyerId ? 'text-danger' : 'text-success'}>
                  <span className="text-xs">{tx.buyerId ? '-' : '+'}</span>
                  <span className="font-mono text-sm">{formatAmount(tx.amount)}</span>
                </span>
              </td>
              <td className="py-2.5 pr-3">
                <span className={`text-xs font-rajdhani ${typeColors[tx.transactionType] || 'text-text-secondary'}`}>
                  {tx.transactionType}
                </span>
              </td>
              <td className="py-2.5">
                <StatusBadge status={tx.status} size="sm" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
