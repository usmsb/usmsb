/** HealthPage - 系统健康状态 */
import { useQuery } from '@tanstack/react-query'
import { fetchSystemHealth } from '../../api/adminApi'
import { Activity, Server, Database, Zap } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { ProgressBar } from '../../components/shared/ProgressBar'

export default function HealthPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'system', 'health'],
    queryFn: fetchSystemHealth,
    refetchInterval: 30000,
  })

  const components = data?.components ?? {}

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">系统健康状态</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="系统状态"
          value={data?.status === 'healthy' ? '健康' : data?.status ?? '未知'}
          icon={Activity}
          color={data?.status === 'healthy' ? 'success' : 'danger'}
          loading={isLoading}
        />
        <StatCard title="CPU 使用率" value={`${(data?.cpu_percent ?? 0).toFixed(1)}%`} icon={Zap} color="info" loading={isLoading} />
        <StatCard title="内存使用率" value={`${(data?.memory_percent ?? 0).toFixed(1)}%`} icon={Server} color="info" loading={isLoading} />
        <StatCard title="数据库大小" value={`${(data?.db_size_mb ?? 0).toFixed(2)} MB`} icon={Database} color="primary" loading={isLoading} />
      </div>

      {/* 资源使用 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
        <h3 className="text-text-primary font-rajdhani font-semibold mb-4">资源使用情况</h3>
        <div className="space-y-4 max-w-xl">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-text-secondary">CPU</span>
              <span className="text-text-primary font-mono">{(data?.cpu_percent ?? 0).toFixed(1)}%</span>
            </div>
            <ProgressBar percent={data?.cpu_percent ?? 0} />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-text-secondary">内存</span>
              <span className="text-text-primary font-mono">{(data?.memory_percent ?? 0).toFixed(1)}%</span>
            </div>
            <ProgressBar percent={data?.memory_percent ?? 0} />
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-text-secondary">磁盘</span>
              <span className="text-text-primary font-mono">{((data?.disk_percent ?? 0)).toFixed(2)} MB</span>
            </div>
            <ProgressBar percent={Math.min((data?.disk_percent ?? 0), 100)} />
          </div>
        </div>
      </div>

      {/* 服务组件状态 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
        <h3 className="text-text-primary font-rajdhani font-semibold mb-4">服务组件</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(components).map(([name, status]) => (
            <div key={name} className="flex items-center gap-3 p-3 bg-bg-tertiary rounded-lg">
              <div className={`w-2 h-2 rounded-full ${status === 'healthy' || status === 'ok' ? 'bg-success animate-pulse' : status === 'degraded' ? 'bg-warning' : 'bg-danger'}`} />
              <span className="text-text-primary text-sm">{name}</span>
              <span className="ml-auto text-text-muted text-xs capitalize">{status as string}</span>
            </div>
          ))}
          {Object.keys(components).length === 0 && (
            <p className="text-text-muted text-sm col-span-3">暂无组件数据</p>
          )}
        </div>
      </div>
    </div>
  )
}
