/** MatchingPage - 匹配分析 */
import { useQuery } from '@tanstack/react-query'
import { fetchMatching } from '../../api/adminApi'
import { TrendingUp, Target } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function MatchingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'matching'],
    queryFn: fetchMatching,
    refetchInterval: 60000,
  })

  const funnel = data?.funnel ?? { published: 0, negotiating: 0, matched: 0, completed: 0 }
  const successRate = data?.success_rate ?? 0
  const topServices = data?.top_services ?? []

  const funnelSteps = [
    { label: '发布需求', value: funnel.published, color: 'bg-neon-blue' },
    { label: 'AI 推荐匹配', value: funnel.matched, color: 'bg-neon-purple' },
    { label: '发起协商', value: funnel.negotiating, color: 'bg-neon-yellow' },
    { label: '达成合作', value: funnel.matched, color: 'bg-neon-green' },
    { label: '成功交付', value: funnel.completed, color: 'bg-neon-green' },
  ]

  const maxFunnel = Math.max(...funnelSteps.map(s => s.value), 1)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        匹配分析
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="发布需求" value={funnel.published} icon={Target} color="primary" loading={isLoading} />
        <StatCard title="AI 匹配数" value={funnel.matched} icon={TrendingUp} color="info" loading={isLoading} />
        <StatCard title="协商中" value={funnel.negotiating} icon={Target} color="warning" loading={isLoading} />
        <StatCard title="成功率" value={successRate.toFixed(1) + '%'} icon={TrendingUp} color="success" loading={isLoading} />
      </div>

      {/* 漏斗图 */}
      <div className="card hologram p-6">
        <h3 className="text-neon-blue font-cyber font-semibold mb-6">匹配漏斗</h3>
        <div className="space-y-4 max-w-xl">
          {funnelSteps.map((step, i) => (
            <div key={step.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-400">{step.label}</span>
                <span className="text-gray-200 font-mono">
                  {step.value} <span className="text-gray-500 text-xs">
                    ({maxFunnel > 0 ? ((step.value / maxFunnel) * 100).toFixed(1) : 0}%)
                  </span>
                </span>
              </div>
              <div className="h-6 bg-cyber-dark rounded overflow-hidden border border-neon-blue/20">
                <div
                  className={`h-full ${step.color} rounded transition-all`}
                  style={{ width: `${maxFunnel > 0 ? (step.value / maxFunnel) * 100 : 0}%`, boxShadow: `0 0 10px currentColor` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Top Services */}
      <div className="card hologram p-6">
        <h3 className="text-neon-purple font-cyber font-semibold mb-4">热门服务类型</h3>
        {topServices.length === 0 ? (
          <p className="text-gray-500 text-sm">暂无数据</p>
        ) : (
          <div className="space-y-2">
            {topServices.map((svc, i) => (
              <div key={svc.service_type} className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-neon-blue/10 border border-neon-blue/30 flex items-center justify-center text-xs text-neon-blue font-bold">
                  {i + 1}
                </span>
                <span className="text-gray-200 flex-1">{svc.service_type}</span>
                <span className="text-gray-500 font-mono text-sm">{svc.count} 次</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
