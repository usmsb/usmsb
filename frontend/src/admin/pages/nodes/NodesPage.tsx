/**
 * NodesPage - 节点管理
 */
import { useQuery } from '@tanstack/react-query'
import { fetchNodes } from '../../api/adminApi'
import { Server } from 'lucide-react'
import NodeHealthTable from '../dashboard/components/NodeHealthTable'
import StatCard from '../../components/shared/StatCard'

export default function NodesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'nodes'],
    queryFn: () => fetchNodes({ pageSize: 100 }),
    refetchInterval: 30000,
  })

  const nodes = data?.nodes ?? []
  const onlineCount = nodes.filter(n => n.status === 'online').length
  const warningCount = nodes.filter(n => n.status === 'warning').length
  const criticalCount = nodes.filter(n => n.status === 'critical').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary font-rajdhani">节点管理</h1>
          <p className="text-text-muted text-sm mt-1">管理平台所有物理节点</p>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="节点总数" value={nodes.length} icon={Server} color="primary" loading={isLoading} />
        <StatCard title="在线" value={onlineCount} icon={Server} color="success" loading={isLoading} />
        <StatCard title="警告" value={warningCount} icon={Server} color="warning" loading={isLoading} />
        <StatCard title="危险" value={criticalCount} icon={Server} color="danger" loading={isLoading} />
      </div>

      {/* 节点列表 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
        <h3 className="text-text-primary font-rajdhani font-medium mb-4">节点列表</h3>
        <NodeHealthTable nodes={nodes} loading={isLoading} />
      </div>
    </div>
  )
}
