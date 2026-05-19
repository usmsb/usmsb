/**
 * NodeHealthTable - 节点健康状态表格
 */
import StatusBadge from '../../../components/shared/StatusBadge'
import { ProgressBar } from '../../../components/shared/ProgressBar'
import type { NodeListData } from '../../../api/adminApi'

interface Props {
  nodes: NodeListData['nodes']
}

function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp)
  if (seconds < 60) return `${seconds}s前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h前`
  return `${Math.floor(seconds / 86400)}d前`
}

export default function NodeHealthTable({ nodes }: Props) {
  if (!nodes || nodes.length === 0) {
    return (
      <div className="text-center text-text-muted text-sm py-8">
        暂无节点数据
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {nodes.slice(0, 4).map(node => (
        <div key={node.node_id} className="p-3 bg-bg-tertiary rounded-lg">
          <div className="flex justify-between items-center mb-2">
            <span className="text-text-primary text-sm font-medium">{node.name}</span>
            <StatusBadge status={node.status} size="sm" />
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-text-muted">Agent: </span>
              <span className="text-text-secondary">{node.agent_count}</span>
            </div>
            <div>
              <span className="text-text-muted">CPU: </span>
              <span className={node.cpu_percent > 80 ? 'text-danger' : 'text-text-secondary'}>
                {node.cpu_percent.toFixed(0)}%
              </span>
            </div>
            <div>
              <span className="text-text-muted">MEM: </span>
              <span className={node.memory_percent > 80 ? 'text-danger' : 'text-text-secondary'}>
                {node.memory_percent.toFixed(0)}%
              </span>
            </div>
          </div>
          <div className="mt-2">
            <ProgressBar percent={node.cpu_percent} />
          </div>
          <p className="text-text-muted text-xs mt-1">
            最后活跃: {node.last_heartbeat ? timeAgo(node.last_heartbeat) : '-'}
          </p>
        </div>
      ))}
    </div>
  )
}
