/** LogsPage - 日志查看 */
import { useQuery } from '@tanstack/react-query'
import { fetchSystemLogs } from '../../api/adminApi'
import { useState } from 'react'

const LEVEL_COLORS: Record<string, string> = {
  INFO: 'text-info',
  WARNING: 'text-warning',
  ERROR: 'text-danger',
  DEBUG: 'text-text-muted',
}

export default function LogsPage() {
  const [page, setPage] = useState(1)
  const [level, setLevel] = useState('')
  const [search, setSearch] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'system', 'logs', page, level, search],
    queryFn: () => fetchSystemLogs({ page, page_size: 50, level: level || undefined, search: search || undefined }),
    refetchInterval: 30000,
  })

  const logs = data?.logs ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / 50))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">日志查看</h1>

      <div className="flex gap-3 items-center">
        <select
          value={level}
          onChange={e => { setLevel(e.target.value); setPage(1) }}
          className="bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-3 py-2 text-sm outline-none"
        >
          <option value="">全部级别</option>
          <option value="INFO">INFO</option>
          <option value="WARNING">WARNING</option>
          <option value="ERROR">ERROR</option>
          <option value="DEBUG">DEBUG</option>
        </select>
        <input
          type="text"
          placeholder="搜索日志内容..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="flex-1 bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-3 py-2 text-sm outline-none placeholder-text-muted"
        />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden font-mono text-xs">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-bg-tertiary rounded animate-pulse" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center text-text-muted py-12">暂无日志数据</div>
        ) : (
          <div className="max-h-[60vh] overflow-auto">
            {logs.map((log: Record<string, unknown>, i: number) => {
              const level = (log.level as string || 'INFO').toUpperCase()
              return (
                <div key={i} className="flex gap-3 px-4 py-2 border-b border-border-primary/30 hover:bg-bg-tertiary/30">
                  <span className={`shrink-0 font-bold ${LEVEL_COLORS[level] || 'text-text-muted'}`}>
                    {level}
                  </span>
                  <span className="text-text-muted shrink-0">
                    {log.timestamp as string || log.created_at ? new Date(((log.timestamp || log.created_at) as number) * 1000).toLocaleString() : '-'}
                  </span>
                  <span className="text-text-primary flex-1 break-all">
                    {String(log.message || log.msg || JSON.stringify(log))}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border-primary">
            <span className="text-text-muted text-sm">共 {total} 条日志</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-50 text-sm">
                上一页
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-50 text-sm">
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
