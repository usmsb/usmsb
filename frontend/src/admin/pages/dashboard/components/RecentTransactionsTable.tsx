/**
 * RecentTransactionsTable - 最近交易表格
 */
import StatusBadge from '../../../components/shared/StatusBadge'
import type { TransactionListData } from '../../../api/adminApi'

function shortAddr(addr: string): string {
  if (!addr || addr.length < 12) return addr || '-'
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp)
  if (seconds < 60) return `${seconds}s前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h前`
  return `${Math.floor(seconds / 86400)}d前`
}

interface Props {
  transactions: TransactionListData['transactions']
}

export default function RecentTransactionsTable({ transactions }: Props) {
  if (!transactions || transactions.length === 0) {
    return (
      <div className="text-center text-gray-500 text-sm py-8">
        暂无交易记录
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neon-blue/20">
            <th className="text-left text-gray-500 font-cyber font-normal pb-2">类型</th>
            <th className="text-left text-gray-500 font-cyber font-normal pb-2">金额</th>
            <th className="text-left text-gray-500 font-cyber font-normal pb-2">状态</th>
            <th className="text-left text-gray-500 font-cyber font-normal pb-2">时间</th>
          </tr>
        </thead>
        <tbody>
          {transactions.slice(0, 5).map(tx => (
            <tr key={tx.tx_id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
              <td className="py-2 text-gray-400 font-mono text-xs">
                {shortAddr(tx.from_address)}
              </td>
              <td className="py-2">
                <span className={`font-mono ${tx.amount >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
                  {tx.amount >= 0 ? '+' : ''}{tx.amount.toFixed(2)}
                </span>
              </td>
              <td className="py-2">
                <StatusBadge status={tx.status} size="sm" />
              </td>
              <td className="py-2 text-gray-500 text-xs">
                {tx.created_at ? timeAgo(tx.created_at) : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
