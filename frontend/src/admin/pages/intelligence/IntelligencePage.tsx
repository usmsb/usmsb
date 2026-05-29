/** IntelligencePage - AI 能力分析 */
import { useQuery } from '@tanstack/react-query'
import { fetchIntelligence } from '../../api/adminApi'
import { Brain, Cpu, Zap } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function IntelligencePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'intelligence'],
    queryFn: fetchIntelligence,
    refetchInterval: 60000,
  })

  const topCaps = data?.top_capabilities ?? []
  const llmCalls = data?.llm_calls_total ?? 0
  const activeSessions = data?.active_sessions ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        AI 能力分析
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="LLM 调用总数" value={llmCalls} icon={Cpu} color="primary" loading={isLoading} />
        <StatCard title="活跃会话" value={activeSessions} icon={Zap} color="warning" loading={isLoading} />
        <StatCard title="平均响应时间" value={`${(data?.avg_response_time ?? 0).toFixed(0)}ms`} icon={Brain} color="info" loading={isLoading} />
        <StatCard title="Token 使用" value={(data?.token_usage?.total ?? 0).toLocaleString()} icon={Zap} color="success" loading={isLoading} />
      </div>

      {/* 能力分布 */}
      <div className="card hologram p-6">
        <h3 className="text-neon-blue font-cyber font-semibold mb-4">Agent 能力分布 Top 10</h3>
        {topCaps.length === 0 ? (
          <p className="text-gray-500 text-sm">暂无能力数据</p>
        ) : (
          <div className="space-y-3">
            {topCaps.map((cap, i) => (
              <div key={cap.capability} className="flex items-center gap-3">
                <span className="w-6 h-6 rounded-full bg-neon-blue/10 border border-neon-blue/30 flex items-center justify-center text-xs text-neon-blue font-bold shrink-0">
                  {i + 1}
                </span>
                <span className="text-gray-200 flex-1">{cap.capability}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 h-2 bg-cyber-dark rounded overflow-hidden border border-neon-blue/20">
                    <div
                      className="h-full bg-neon-blue rounded"
                      style={{ width: `${Math.min(100, (cap.count / Math.max(...topCaps.map(c => c.count), 1)) * 100)}%`, boxShadow: '0 0 10px #00f5ff' }}
                    />
                  </div>
                  <span className="text-gray-500 text-xs font-mono w-12 text-right">{cap.count}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
