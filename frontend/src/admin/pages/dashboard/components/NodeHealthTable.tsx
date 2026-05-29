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
      <div className="text-center text-gray-500 text-sm py-8">
        暂无节点数据
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {nodes.slice(0, 4).map(node => (
        <div key={node.node_id} className="p-3 bg-cyber-dark/50 rounded-lg border border-neon-blue/10">
          <div className="flex justify-between items-center mb-2">
            <span className="text-gray-200 text-sm font-cyber font-medium">{node.name}</span>
            <StatusBadge status={node.status} size="sm" />
          </div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            <div>
              <span className="text-gray-500">Agent: </span>
              <span className="text-neon-blue">{node.agent_count}</span>
            </div>
            <div>
              <span className="text-gray-500">CPU: </span>
              <span className={node.cpu_percent > 80 ? 'text-neon-red' : 'text-neon-green'}>
                {node.cpu_percent.toFixed(0)}%
              </span>
            </div>
            <div>
              <span className="text-gray-500">MEM: </span>
              <span className={node.memory_percent > 80 ? 'text-neon-red' : 'text-neon-green'}>
                {node.memory_percent.toFixed(0)}%
              </span>
            </div>
          </div>
          <div className="mt-2">
            <ProgressBar percent={node.cpu_percent} />
          </div>
          <p className="text-gray-500 text-xs mt-1">
            最后活跃: {node.last_heartbeat ? timeAgo(node.last_heartbeat) : '-'}
          </p>
        </div>
      ))}
    </div>
  )
}
