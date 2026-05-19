/** PermissionsPage - 权限矩阵 */
import { useQuery } from '@tanstack/react-query'
import { fetchPermissions } from '../../api/adminApi'
import { Shield } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function PermissionsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'permissions'],
    queryFn: fetchPermissions,
    refetchInterval: 120000,
  })

  const matrix = data?.matrix ?? []
  const roles = data?.roles ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">权限矩阵</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="权限项" value={matrix.length} icon={Shield} color="primary" loading={isLoading} />
        <StatCard title="角色数" value={roles.length} icon={Shield} color="info" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal sticky left-0 bg-bg-tertiary">权限项</th>
                {roles.map(role => (
                  <th key={role} className="text-center px-4 py-3 text-text-muted font-normal min-w-[100px]">{role}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(6)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    <td className="px-4 py-3"><div className="h-4 w-32 bg-bg-tertiary rounded animate-pulse" /></td>
                    {roles.map(r => (
                      <td key={r} className="px-4 py-3"><div className="h-4 w-8 bg-bg-tertiary rounded animate-pulse mx-auto" /></td>
                    ))}
                  </tr>
                ))
              ) : matrix.length === 0 ? (
                <tr>
                  <td colSpan={roles.length + 1} className="text-center text-text-muted py-12">暂无权限数据</td>
                </tr>
              ) : (
                matrix.map((row: Record<string, unknown>, i: number) => (
                  <tr key={i} className="border-b border-border-primary/50 hover:bg-bg-tertiary/30 transition-colors">
                    <td className="px-4 py-3 text-text-secondary sticky left-0 bg-bg-secondary font-mono text-xs">
                      {row.permission as string}
                    </td>
                    {roles.map(role => (
                      <td key={role} className="px-4 py-3 text-center">
                        {row[role] ? (
                          <span className="text-success text-lg">✓</span>
                        ) : (
                          <span className="text-danger text-lg">✗</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
