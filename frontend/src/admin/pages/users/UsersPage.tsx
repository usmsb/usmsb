/** UsersPage - 用户管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchUsers } from '../../api/adminApi'
import { Users } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'
import { useState } from 'react'

const ROLE_LABELS: Record<string, string> = {
  superadmin: '超级管理员',
  node_admin: '节点管理员',
  developer: '开发人员',
  node_operator: '节点运营',
  human: '普通用户',
  ai_owner: 'AI 主人',
  ai_agent: 'AI Agent',
}

function shortAddr(addr: string): string {
  if (!addr || addr.length < 12) return addr || '-'
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

export default function UsersPage() {
  const [page, setPage] = useState(1)
  const [roleFilter, setRoleFilter] = useState<string>('')

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', page, roleFilter],
    queryFn: () => fetchUsers({ page, page_size: 20, role: roleFilter || undefined }),
    refetchInterval: 60000,
  })

  const users = data?.users ?? []
  const total = data?.total ?? 0
  const totalPages = data?.total_pages ?? 1

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">用户管理</h1>

      {/* 过滤器 */}
      <div className="flex gap-3 items-center">
        <select
          value={roleFilter}
          onChange={e => { setRoleFilter(e.target.value); setPage(1) }}
          className="bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-3 py-2 text-sm outline-none"
        >
          <option value="">全部角色</option>
          {Object.entries(ROLE_LABELS).map(([val, label]) => (
            <option key={val} value={val}>{label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总用户" value={total} icon={Users} color="primary" loading={isLoading} />
        <StatCard title="管理员" value={users.filter(u => ['superadmin', 'node_admin'].includes(u.user_role)).length} icon={Users} color="danger" loading={isLoading} />
        <StatCard title="普通用户" value={users.filter(u => u.user_role === 'human').length} icon={Users} color="info" loading={isLoading} />
        <StatCard title="本页" value={users.length} icon={Users} color="success" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">地址</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">角色</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">质押额</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">余额</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">状态</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-36 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 bg-bg-tertiary rounded animate-pulse" /></td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center text-text-muted py-12">暂无用户数据</td>
                </tr>
              ) : (
                users.map(user => (
                  <tr key={user.user_id} className="border-b border-border-primary/50 hover:bg-bg-tertiary/50 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                      {shortAddr(user.address)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={user.user_role} size="sm" />
                    </td>
                    <td className="px-4 py-3 font-mono text-text-primary">
                      {user.stake_amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 font-mono text-text-secondary">
                      {user.balance.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={user.status} size="sm" />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border-primary">
            <span className="text-text-muted text-sm">
              第 {page} / {totalPages} 页，共 {total} 条
            </span>
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
