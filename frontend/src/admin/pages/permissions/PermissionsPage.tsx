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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        权限矩阵
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="权限项" value={matrix.length} icon={Shield} color="primary" loading={isLoading} />
        <StatCard title="角色数" value={roles.length} icon={Shield} color="info" loading={isLoading} />
      </div>

      <div className="card hologram overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal sticky left-0 bg-cyber-dark/50">权限项</th>
                {roles.map(role => (
                  <th key={role} className="text-center px-4 py-3 text-gray-500 font-cyber font-normal min-w-[100px]">{role}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                [...Array(6)].map((_, i) => (
                  <tr key={i} className="border-b border-neon-blue/10">
                    <td className="px-4 py-3"><div className="h-4 w-32 bg-cyber-dark rounded animate-pulse" /></td>
                    {roles.map(r => (
                      <td key={r} className="px-4 py-3"><div className="h-4 w-8 bg-cyber-dark rounded animate-pulse mx-auto" /></td>
                    ))}
                  </tr>
                ))
              ) : matrix.length === 0 ? (
                <tr>
                  <td colSpan={roles.length + 1} className="text-center text-gray-500 py-12">暂无权限数据</td>
                </tr>
              ) : (
                matrix.map((row: Record<string, unknown>, i: number) => (
                  <tr key={i} className="border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                    <td className="px-4 py-3 text-gray-400 sticky left-0 bg-inherit font-mono text-xs">
                      {row.permission as string}
                    </td>
                    {roles.map(role => (
                      <td key={role} className="px-4 py-3 text-center">
                        {row[role] ? (
                          <span className="text-neon-green text-lg">✓</span>
                        ) : (
                          <span className="text-neon-red text-lg">✗</span>
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
