/** LogsPage - 日志查看 */
import { useQuery } from '@tanstack/react-query'
import { fetchSystemLogs } from '../../api/adminApi'
import { useState } from 'react'

const LEVEL_COLORS: Record<string, string> = {
  INFO: 'text-neon-blue',
  WARNING: 'text-neon-yellow',
  ERROR: 'text-neon-red',
  DEBUG: 'text-gray-500',
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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        日志查看
      </h1>

      <div className="flex gap-3 items-center">
        <select
          value={level}
          onChange={e => { setLevel(e.target.value); setPage(1) }}
          className="input"
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
          className="flex-1 input"
        />
      </div>

      <div className="card hologram overflow-hidden font-mono text-xs">
        {isLoading ? (
          <div className="p-4 space-y-2">
            {[...Array(8)].map((_, i) => (
              <div key={i} className="h-4 bg-cyber-dark rounded animate-pulse" />
            ))}
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center text-gray-500 py-12">暂无日志数据</div>
        ) : (
          <div className="max-h-[60vh] overflow-auto">
            {logs.map((log: Record<string, unknown>, i: number) => {
              const lvl = (log.level as string || 'INFO').toUpperCase()
              return (
                <div key={i} className="flex gap-3 px-4 py-2 border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                  <span className={`shrink-0 font-bold ${LEVEL_COLORS[lvl] || 'text-gray-500'}`}>
                    {lvl}
                  </span>
                  <span className="text-gray-600 shrink-0">
                    {log.timestamp as string || log.created_at ? new Date(((log.timestamp || log.created_at) as number) * 1000).toLocaleString() : '-'}
                  </span>
                  <span className="text-gray-300 flex-1 break-all">
                    {String(log.message || log.msg || JSON.stringify(log))}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-neon-blue/20">
            <span className="text-gray-500 text-sm font-cyber">共 {total} 条日志</span>
            <div className="flex gap-2">
              <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all">
                上一页
              </button>
              <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg bg-cyber-card border border-neon-blue/30 text-gray-400 hover:text-neon-blue hover:border-neon-blue/50 disabled:opacity-50 text-sm font-cyber transition-all">
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
