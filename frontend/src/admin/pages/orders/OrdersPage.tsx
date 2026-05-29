/** OrdersPage - 订单管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchOrders } from '../../api/adminApi'
import { ClipboardList } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { useState } from 'react'

export default function OrdersPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'orders', page],
    queryFn: () => fetchOrders({ page, page_size: 20 }),
    refetchInterval: 60000,
  })

  const orders = data?.orders ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  // Compute stats from orders
  const completed = orders.filter(o => o.status === 'completed').length
  const pending = orders.filter(o => ['pending', 'open', 'negotiating'].includes(o.status)).length

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        订单管理
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总订单" value={total} icon={ClipboardList} color="primary" loading={isLoading} />
        <StatCard title="待处理" value={pending} icon={ClipboardList} color="warning" loading={isLoading} />
        <StatCard title="已完成" value={completed} icon={ClipboardList} color="success" loading={isLoading} />
        <StatCard title="总页数" value={totalPages} icon={ClipboardList} color="info" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">订单ID</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">创建者</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">服务类型</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">预算</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">已花费</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-32 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-cyber-dark rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center text-gray-500 py-12">暂无订单数据</td>
                </tr>
              ) : (
                orders.map(order => (
                  <tr key={order.order_id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-neon-blue">
                      {order.order_id.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-400">
                      {order.creator?.slice(0, 8)}...
                    </td>
                    <td className="px-4 py-3 text-gray-200">
                      {order.service_type || '-'}
                    </td>
                    <td className="px-4 py-3 text-neon-green font-mono">
                      {order.total_budget.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-gray-400 font-mono">
                      {order.spent.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={order.status} size="sm" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neon-blue/20">
            <span className="text-gray-500 text-sm font-cyber">
              第 {page} / {totalPages} 页，共 {total} 条
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all"
              >
                上一页
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
