/** GeneCapsulesPage - Gene Capsule 探索 */
import { useQuery } from '@tanstack/react-query'
import { fetchGeneCapsules } from '../../api/adminApi'
import { Brain } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import { useState } from 'react'

export default function GeneCapsulesPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'gene-capsules', page],
    queryFn: () => fetchGeneCapsules({ page, page_size: 20 }),
    refetchInterval: 120000,
  })

  const capsules = data?.capsules ?? []
  const total = data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(total / 20))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">Gene Capsule 探索</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard title="总 Capsule" value={total} icon={Brain} color="primary" loading={isLoading} />
        <StatCard title="本页" value={capsules.length} icon={Brain} color="info" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">Capsule ID</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">类型</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">创建时间</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(3)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-32 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : capsules.length === 0 ? (
                <tr>
                  <td colSpan={3} className="text-center text-text-muted py-12">暂无 Gene Capsule 数据</td>
                </tr>
              ) : (
                capsules.map((capsule: Record<string, unknown>, i: number) => (
                  <tr key={i} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {(capsule.capsule_id as string || capsule.id as string || `capsule-${i}`).slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-text-primary">
                      {(capsule.gene_type || capsule.type || 'unknown') as string}
                    </td>
                    <td className="px-4 py-3 text-text-muted text-xs">
                      {capsule.created_at
                        ? new Date((capsule.created_at as number) * 1000).toLocaleString()
                        : '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border-primary">
            <span className="text-text-muted text-sm">第 {page} / {totalPages} 页，共 {total} 条</span>
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
