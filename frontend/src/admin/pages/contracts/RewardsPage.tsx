/** RewardsPage - 奖励分发 */
import { Coins } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function RewardsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">奖励分发</h1>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard title="Builder 奖池" value="-" icon={Coins} color="primary" />
        <StatCard title="Dev 奖池" value="-" icon={Coins} color="info" />
        <StatCard title="Node 奖池" value="-" icon={Coins} color="success" />
        <StatCard title="Output 奖池" value="-" icon={Coins} color="warning" />
        <StatCard title="协作项目" value="-" icon={Coins} color="primary" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">Builder / Dev / Node / Output / 协作 奖励页面开发中...</p>
      </div>
    </div>
  )
}
