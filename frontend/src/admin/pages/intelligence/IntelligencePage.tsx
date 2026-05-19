/** IntelligencePage - AI 能力分析 */
import { Brain } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function IntelligencePage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">AI 能力分析</h1>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="LLM 总调用" value="-" icon={Brain} color="primary" />
        <StatCard title="成功率" value="-" icon={Brain} color="success" />
        <StatCard title="平均延迟" value="-" icon={Brain} color="warning" />
        <StatCard title="Token 消耗" value="-" icon={Brain} color="info" />
      </div>
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-8 text-center">
        <p className="text-text-muted">AI 能力分析功能开发中...</p>
      </div>
    </div>
  )
}
