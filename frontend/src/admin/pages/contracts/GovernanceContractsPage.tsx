/** GovernanceContractsPage - 治理合约 */
import { Vote } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function GovernanceContractsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">治理合约</h1>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard title="总投票权" value="-" icon={Vote} color="primary" />
        <StatCard title="提案总数" value="-" icon={Vote} color="info" />
        <StatCard title="活跃提案" value="-" icon={Vote} color="success" />
        <StatCard title="投票参与率" value="-" icon={Vote} color="warning" suffix="%" />
        <StatCard title="争议数" value="-" icon={Vote} color="danger" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">提案 / 委托 / 争议 / 贡献积分页面开发中...</p>
      </div>
    </div>
  )
}
