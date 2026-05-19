/** PermissionsPage - 权限管理 */
import { Shield } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

const permissions = [
  'Agent创建', '交易', '节点管理', '用户管理', '系统配置', '治理投票', '合约读', '合约写'
]

const roles = ['superadmin', 'node_admin', 'node_operator', 'ai_owner', 'human', 'ai_agent']

const permissionMatrix: Record<string, boolean[]> = {
  superadmin:   [true,  true,  true,  true,  true,  true,  true,  true ],
  node_admin:   [true,  true,  true,  false, false, true,  true,  false],
  node_operator:[false, true,  false, false, false, false, true,  false],
  ai_owner:    [true,  true,  false, false, false, false, true,  false],
  human:        [false, true,  false, false, false, true,  true,  false],
  ai_agent:     [false, true,  false, false, false, false, true,  false],
}

export default function PermissionsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">权限管理</h1>

      {/* 权限矩阵 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="p-4 border-b border-border-primary">
          <h3 className="text-text-primary font-rajdhani font-medium">权限矩阵</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border-primary">
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4 sticky left-0 bg-bg-secondary">角色</th>
                {permissions.map(p => (
                  <th key={p} className="text-center text-text-muted text-xs font-medium py-3 px-3 min-w-[80px]">{p}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {roles.map(role => (
                <tr key={role} className="hover:bg-bg-tertiary/50">
                  <td className="py-3 px-4 sticky left-0 bg-bg-secondary">
                    <span className="text-text-primary text-sm font-medium">{role}</span>
                  </td>
                  {permissionMatrix[role]?.map((allowed, i) => (
                    <td key={i} className="text-center py-3 px-3">
                      {allowed
                        ? <span className="text-success text-lg">✓</span>
                        : <span className="text-danger text-lg">✗</span>}
                    </td>
                  )) ?? <td colSpan={8} />}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <StatCard title="超级管理员" value={1} icon={Shield} color="danger" />
        <StatCard title="节点管理员" value="-" icon={Shield} color="warning" />
        <StatCard title="节点运营" value="-" icon={Shield} color="info" />
      </div>
    </div>
  )
}
