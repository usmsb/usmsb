/** UsersPage - 用户管理 */
import { useQuery } from '@tanstack/react-query'
import { fetchUsers } from '../../api/adminApi'
import { Users } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import StatusBadge from '../../components/shared/StatusBadge'

export default function UsersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => fetchUsers({ pageSize: 100 }),
  })

  const users = data?.users ?? []

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">用户管理</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="总用户" value={data?.total ?? 0} icon={Users} color="primary" loading={isLoading} />
        <StatCard title="已质押" value={users.filter(u => u.stakeStatus === 'staked').length} icon={Users} color="success" loading={isLoading} />
        <StatCard title="AI Owner" value={users.filter(u => u.role === 'ai_owner').length} icon={Users} color="info" loading={isLoading} />
        <StatCard title="Node Admin" value={users.filter(u => u.role === 'node_admin').length} icon={Users} color="warning" loading={isLoading} />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-bg-tertiary border-b border-border-primary">
              <tr>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">钱包地址</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">角色</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">Stake</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">Stake状态</th>
                <th className="text-left text-text-muted text-xs font-medium py-3 px-4">操作</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-primary">
              {isLoading ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted">加载中...</td></tr>
              ) : users.length === 0 ? (
                <tr><td colSpan={5} className="py-8 text-center text-text-muted text-sm">暂无数据</td></tr>
              ) : (
                users.map(user => (
                  <tr key={user.walletAddress} className="hover:bg-bg-tertiary/50">
                    <td className="py-3 px-4">
                      <p className="text-text-primary text-xs font-mono">{user.walletAddress.slice(0, 10)}...{user.walletAddress.slice(-4)}</p>
                    </td>
                    <td className="py-3 px-4"><StatusBadge status={user.role} size="sm" /></td>
                    <td className="py-3 px-4"><span className="text-text-primary text-sm">{Number(user.stake).toLocaleString()} VIBE</span></td>
                    <td className="py-3 px-4"><StatusBadge status={user.stakeStatus} size="sm" /></td>
                    <td className="py-3 px-4"><button className="text-primary text-sm hover:underline">编辑</button></td>
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
