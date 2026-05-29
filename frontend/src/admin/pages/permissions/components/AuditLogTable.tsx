// AuditLogTable.tsx - 审计日志表格
import TimeAgo from '../../../components/shared/TimeAgo'

export interface AuditLog {
  id: string
  timestamp: number
  user: string
  action: string
  resource: string
  details?: string
  ip?: string
  status: 'success' | 'failed' | 'warning'
}

interface AuditLogTableProps {
  logs: AuditLog[]
  isLoading?: boolean
  className?: string
}

const STATUS_STYLES = {
  success: 'text-neon-green bg-neon-green/10 border border-neon-green/30',
  failed: 'text-neon-red bg-neon-red/10 border border-neon-red/30',
  warning: 'text-neon-yellow bg-neon-yellow/10 border border-neon-yellow/30',
}

export default function AuditLogTable({ logs, isLoading, className = '' }: AuditLogTableProps) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
            <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">时间</th>
            <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">用户</th>
            <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">操作</th>
            <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">资源</th>
            <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">详情</th>
            <th className="text-center px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            [...Array(8)].map((_, i) => (
              <tr key={i} className="border-b border-neon-blue/10">
                {[...Array(6)].map((_, j) => (
                  <td key={j} className="px-4 py-3"><div className="h-4 bg-cyber-dark rounded animate-pulse" /></td>
                ))}
              </tr>
            ))
          ) : logs.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-gray-500 py-12 font-cyber">暂无审计日志</td>
            </tr>
          ) : (
            logs.map(log => (
              <tr key={log.id} className="border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                <td className="px-4 py-3 text-gray-500 text-xs">
                  <TimeAgo timestamp={log.timestamp * 1000} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-gray-400">
                  {log.user.slice(0, 6)}...{log.user.slice(-4)}
                </td>
                <td className="px-4 py-3 text-gray-200 text-xs font-cyber">
                  {log.action}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs font-cyber">
                  {log.resource}
                </td>
                <td className="px-4 py-3 text-gray-500 text-xs max-w-[200px] truncate font-cyber">
                  {log.details || '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium font-cyber ${STATUS_STYLES[log.status]}`}>
                    {log.status === 'success' ? '成功' : log.status === 'failed' ? '失败' : '警告'}
                  </span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
