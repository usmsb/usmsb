// AdminRoute.tsx - 管理员路由守卫
import { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

const ADMIN_ROLES = ['superadmin', 'node_admin', 'operator'] as const

interface AdminRouteProps {
  children: ReactNode
  requiredRoles?: readonly string[]
}

export default function AdminRoute({
  children,
  requiredRoles = ADMIN_ROLES,
}: AdminRouteProps) {
  const userRole = useAuthStore(s => s.userRole)
  const isConnected = useAuthStore(s => s.isConnected)

  if (!isConnected) {
    return <Navigate to="/admin" replace />
  }

  if (!userRole || !requiredRoles.includes(userRole)) {
    return <Navigate to="/admin/dashboard" replace />
  }

  return <>{children}</>
}
