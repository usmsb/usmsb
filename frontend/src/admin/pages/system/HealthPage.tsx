/** HealthPage - 服务健康状态 */
import { useQuery } from '@tanstack/react-query'
import { fetchHealth } from '../../api/adminApi'
import { Settings } from 'lucide-react'
import StatusBadge from '../../components/shared/StatusBadge'

export default function HealthPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['admin', 'system', 'health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  })

  const services = data?.services ?? []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary font-rajdhani">服务健康状态</h1>
        <button onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-bg-tertiary rounded-lg text-text-secondary hover:text-text-primary text-sm transition-colors">
          <Settings className="w-4 h-4" />
          重新检查
        </button>
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <table className="w-full">
          <thead className="bg-bg-tertiary border-b border-border-primary">
            <tr>
              <th className="text-left text-text-muted text-xs font-medium py-3 px-4">服务</th>
              <th className="text-left text-text-muted text-xs font-medium py-3 px-4">状态</th>
              <th className="text-left text-text-muted text-xs font-medium py-3 px-4">延迟</th>
              <th className="text-left text-text-muted text-xs font-medium py-3 px-4">详情</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-primary">
            {isLoading ? (
              <tr><td colSpan={4} className="py-8 text-center text-text-muted">加载中...</td></tr>
            ) : services.length === 0 ? (
              <tr><td colSpan={4} className="py-8 text-center text-text-muted text-sm">暂无服务数据</td></tr>
            ) : (
              services.map(svc => (
                <tr key={svc.name} className="hover:bg-bg-tertiary/50">
                  <td className="py-3 px-4">
                    <span className="text-text-primary text-sm font-medium">{svc.name}</span>
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge
                      status={svc.status === 'ok' ? 'ok' : svc.status === 'degraded' ? 'degraded' : 'down'}
                      size="sm"
                      pulse={svc.status === 'down'}
                    />
                  </td>
                  <td className="py-3 px-4">
                    <span className={`text-sm font-mono ${
                      svc.latencyMs < 100 ? 'text-success' :
                      svc.latencyMs < 1000 ? 'text-warning' : 'text-danger'
                    }`}>
                      {svc.latencyMs}ms
                    </span>
                  </td>
                  <td className="py-3 px-4 text-text-muted text-xs">
                    {svc.message || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
