/**
 * NodeHealthTable - 节点健康表格
 */
import StatusBadge from '../../../components/shared/StatusBadge'
import { ProgressBar } from '../../../components/shared/ProgressBar'
import type { NodeHealth } from '../../../api/adminApi'

interface NodeHealthTableProps {
  nodes: NodeHealth[]
  loading?: boolean
}

function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp)
  if (seconds < 60) return `${seconds}秒前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时前`
  return `${Math.floor(seconds / 86400)}天前`
}

export default function NodeHealthTable({ nodes, loading }: NodeHealthTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-12 bg-bg-tertiary rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (!nodes || nodes.length === 0) {
    return (
      <div className="text-center py-8 text-text-muted text-sm">
        暂无节点数据
      </div>
    )
  }

  // 显示前 5 个
  const displayNodes = nodes.slice(0, 5)

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border-primary">
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-4">节点</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-4">状态</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-4">Agent</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-4">CPU</th>
            <th className="text-left text-text-muted text-xs font-medium py-2 pr-4">内存</th>
            <th className="text-left text-text-muted text-xs font-medium py-2">心跳</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-primary">
          {displayNodes.map(node => (
            <tr key={node.nodeId} className="hover:bg-bg-tertiary/50 transition-colors">
              <td className="py-3 pr-4">
                <div>
                  <p className="text-text-primary text-sm font-medium">{node.name}</p>
                  <p className="text-text-muted text-xs font-mono">{node.ip || node.nodeId.slice(0, 12)}</p>
                </div>
              </td>
              <td className="py-3 pr-4">
                <StatusBadge
                  status={node.status === 'warning' ? 'warning' :
                          node.status === 'critical' ? 'critical' :
                          node.status === 'maintenance' ? 'maintenance' : 'online'}
                  size="sm"
                />
              </td>
              <td className="py-3 pr-4">
                <span className="text-text-primary text-sm font-mono">
                  {node.onlineCount}/{node.agentCount}
                </span>
              </td>
              <td className="py-3 pr-4 min-w-[80px]">
                <ProgressBar
                  percent={node.cpuPercent}
                  warning={70}
                  critical={85}
                  showLabel
                  size="sm"
                />
              </td>
              <td className="py-3 pr-4 min-w-[80px]">
                <ProgressBar
                  percent={node.memoryPercent}
                  warning={75}
                  critical={90}
                  showLabel
                  size="sm"
                />
              </td>
              <td className="py-3">
                <span className="text-text-muted text-xs">
                  {timeAgo(node.lastHeartbeat)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
