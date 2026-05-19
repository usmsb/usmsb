/** OrdersPage - 订单管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchOrders } from '../../api/adminApi'
import { ClipboardList } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'

export default function OrdersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'orders'],
    queryFn: () => fetchOrders({ pageSize: 50 }),
    refetchInterval: 60000,
  })

  const orders = data?.orders ?? []
  const stats = data?.stats

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">订单管理</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总订单" value={stats?.total ?? 0} icon={ClipboardList} color="primary" loading={isLoading} />
        <StatCard title="进行中" value={stats?.inProgress ?? 0} icon={ClipboardList} color="info" loading={isLoading} />
        <StatCard title="已完成" value={stats?.completed ?? 0} icon={ClipboardList} color="success" loading={isLoading} />
        <StatCard title="争议中" value={stats?.disputed ?? 0} icon={ClipboardList} color="danger" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-bg-tertiary border-b border-border-primary">
              <tr>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">订单号</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">需求方</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">状态</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">优先级</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">金额</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {isLoading ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted">加载中...</td></tr>
              ) : orders.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted text-sm">暂无订单数据</td></tr>
              ) : (
                orders.map(order => (
                  <tr key={order.orderId} className="hover:bg-bg-tertiary/50">
                    <td className="py-3 px-4 text-text-primary text-xs font-mono">{order.orderId.slice(0, 16)}...</td>
                    <td className="py-3 px-4 text-text-secondary text-xs font-mono">{order.demandAgentId.slice(0, 12)}...</td>
                    <td className="py-3 px-4"><StatusBadge status={order.status} size="sm" /></td>
                    <td className="py-3 px-4"><StatusBadge status={order.priority} size="sm" /></td>
                    <td className="py-3 px-4 text-text-primary text-sm">{Number(order.vibeLocked).toLocaleString()} VIBE</td>
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
