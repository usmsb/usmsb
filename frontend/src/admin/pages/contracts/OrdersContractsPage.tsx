/** OrdersContractsPage - 订单与协作 */
import { ClipboardList } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function OrdersContractsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">订单与协作</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="订单池总数" value="-" icon={ClipboardList} color="primary" />
        <StatCard title="活跃竞价" value="-" icon={ClipboardList} color="warning" />
        <StatCard title="总交易额" value="-" icon={ClipboardList} color="success" />
        <StatCard title="ZK 凭证" value="-" icon={ClipboardList} color="info" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">JointOrder / 协作 / 资产 / ZK 凭证页面开发中...</p>
      </div>
    </div>
  )
}
