/** MatchingPage - 匹配分析 */
import { useQuery } from '@tanstack/react-query'
import { fetchMatchingFunnel } from '../../api/adminApi'
import { GitMerge } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function MatchingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'matching', 'funnel'],
    queryFn: () => fetchMatchingFunnel('7d'),
    refetchInterval: 60000,
  })

  const funnel = data

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">匹配分析</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="发布需求" value={funnel?.demands ?? 0} icon={GitMerge} color="primary" loading={isLoading} />
        <StatCard title="AI推荐" value={funnel?.aiMatch ?? 0} icon={GitMerge} color="info" loading={isLoading} />
        <StatCard title="达成合作" value={funnel?.agreements ?? 0} icon={GitMerge} color="success" loading={isLoading} />
        <StatCard title="成功交付" value={funnel?.deliveries ?? 0} icon={GitMerge} color="success" loading={isLoading} />
      </div>

      {/* 漏斗可视化 */}
      {funnel && (
        <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
          <h3 className="text-text-primary font-rajdhani font-medium mb-6">匹配漏斗（7天）</h3>
          <div className="max-w-md mx-auto space-y-3">
            {[
              { label: '发布需求', value: funnel.demands, color: 'bg-primary' },
              { label: 'AI 推荐', value: funnel.aiMatch, color: 'bg-info' },
              { label: '发起协商', value: funnel.negotiations, color: 'bg-warning' },
              { label: '达成合作', value: funnel.agreements, color: 'bg-success' },
              { label: '成功交付', value: funnel.deliveries, color: 'bg-success' },
            ].map((item, i) => (
              <div key={item.label} className="relative">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-text-secondary text-sm">{item.label}</span>
                  <span className="text-text-primary font-mono text-sm">{item.value}</span>
                </div>
                <div className="h-8 bg-bg-tertiary rounded overflow-hidden">
                  <div
                    className={`h-full ${item.color} rounded transition-all duration-700`}
                    style={{ width: `${(item.value / funnel.demands) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-4 mt-8">
            <div className="text-center p-4 bg-bg-tertiary rounded-lg">
              <p className="text-text-muted text-xs">平均匹配时长</p>
              <p className="text-text-primary font-orbitron text-lg mt-1">{funnel.avgMatchTime}</p>
            </div>
            <div className="text-center p-4 bg-bg-tertiary rounded-lg">
              <p className="text-text-muted text-xs">达成率</p>
              <p className="text-success font-orbitron text-lg mt-1">{funnel.agreementRate}%</p>
            </div>
            <div className="text-center p-4 bg-bg-tertiary rounded-lg">
              <p className="text-text-muted text-xs">交付成功率</p>
              <p className="text-success font-orbitron text-lg mt-1">{funnel.deliveryRate}%</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
