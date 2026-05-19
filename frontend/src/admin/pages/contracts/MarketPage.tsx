/** MarketPage - 市场数据 */
import { Coins } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function MarketPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">市场数据</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="VIBE 价格" value="-" icon={Coins} color="primary" prefix="$" />
        <StatCard title="7日均价" value="-" icon={Coins} color="info" prefix="$" />
        <StatCard title="总供给" value="-" icon={Coins} color="success" />
        <StatCard title="交易税" value="-" icon={Coins} color="warning" suffix="%" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">Token / 价格预言机 / 归属释放 / 资金池页面开发中...</p>
      </div>
    </div>
  )
}
