// useAdminAuth.ts - 管理员认证 Hook
import { useAuthStore } from '@/stores/authStore'

const ADMIN_ROLES = ['superadmin', 'node_admin', 'operator'] as const
const SUPERADMIN_ROLES = ['superadmin'] as const

export function useAdminAuth() {
  const userRole = useAuthStore(s => s.userRole)
  const isConnected = useAuthStore(s => s.isConnected)
  const address = useAuthStore(s => s.address)

  const isAdmin = isConnected && !!userRole && ADMIN_ROLES.includes(userRole as typeof ADMIN_ROLES[number])
  const isSuperadmin = isConnected && !!userRole && SUPERADMIN_ROLES.includes(userRole as typeof SUPERADMIN_ROLES[number])

  return {
    isAdmin,
    isSuperadmin,
    isConnected,
    userRole,
    address,
    isLoading: !userRole && isConnected, // 加载中：已连接但角色未获取
  }
}

export function requireAdmin(handler?: () => void) {
  const { isAdmin } = useAdminAuth()
  if (!isAdmin) {
    handler?.()
    return false
  }
  return true
}
