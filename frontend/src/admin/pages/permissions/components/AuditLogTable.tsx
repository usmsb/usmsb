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
  success: 'text-success bg-success/10',
  failed: 'text-danger bg-danger/10',
  warning: 'text-warning bg-warning/10',
}

export default function AuditLogTable({ logs, isLoading, className = '' }: AuditLogTableProps) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-primary bg-bg-tertiary">
            <th className="text-left px-4 py-3 text-text-muted font-normal">时间</th>
            <th className="text-left px-4 py-3 text-text-muted font-normal">用户</th>
            <th className="text-left px-4 py-3 text-text-muted font-normal">操作</th>
            <th className="text-left px-4 py-3 text-text-muted font-normal">资源</th>
            <th className="text-left px-4 py-3 text-text-muted font-normal">详情</th>
            <th className="text-center px-4 py-3 text-text-muted font-normal">状态</th>
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            [...Array(8)].map((_, i) => (
              <tr key={i} className="border-b border-border-primary/50">
                {[...Array(6)].map((_, j) => (
                  <td key={j} className="px-4 py-3"><div className="h-4 bg-bg-tertiary rounded animate-pulse" /></td>
                ))}
              </tr>
            ))
          ) : logs.length === 0 ? (
            <tr>
              <td colSpan={6} className="text-center text-text-muted py-12">暂无审计日志</td>
            </tr>
          ) : (
            logs.map(log => (
              <tr key={log.id} className="border-b border-border-primary/50 hover:bg-bg-tertiary/30 transition-colors">
                <td className="px-4 py-3 text-text-muted text-xs">
                  <TimeAgo timestamp={log.timestamp * 1000} />
                </td>
                <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                  {log.user.slice(0, 6)}...{log.user.slice(-4)}
                </td>
                <td className="px-4 py-3 text-text-primary text-xs">
                  {log.action}
                </td>
                <td className="px-4 py-3 text-text-muted text-xs">
                  {log.resource}
                </td>
                <td className="px-4 py-3 text-text-muted text-xs max-w-[200px] truncate">
                  {log.details || '-'}
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[log.status]}`}>
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
