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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        Gene Capsule 探索
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard title="总 Capsule" value={total} icon={Brain} color="primary" loading={isLoading} />
        <StatCard title="本页" value={capsules.length} icon={Brain} color="info" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">Capsule ID</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">类型</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">创建时间</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(3)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-32 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : capsules.length === 0 ? (
                <tr>
                  <td colSpan={3} className="text-center text-gray-500 py-12">暂无 Gene Capsule 数据</td>
                </tr>
              ) : (
                capsules.map((capsule: Record<string, unknown>, i: number) => (
                  <tr key={i} className="border-b border-neon-blue/10 hover:bg-cyber-dark/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-neon-blue">
                      {(capsule.capsule_id as string || capsule.id as string || `capsule-${i}`).slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3 text-gray-200">
                      {(capsule.gene_type || capsule.type || 'unknown') as string}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
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
          <div className="flex items-center justify-between px-4 py-3 border-t border-neon-blue/20">
            <span className="text-gray-500 text-sm font-cyber">第 {page} / {totalPages} 页，共 {total} 条</span>
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
