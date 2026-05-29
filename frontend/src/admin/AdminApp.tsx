/**
 * Admin Panel App Router
 * 管理员专用管理后台路由
 */
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import AdminLayout from './layouts/AdminLayout'

// Pages
import DashboardPage from './pages/dashboard/DashboardPage'
import CommandCenterPage from './pages/command-center/CommandCenterPage'
import NodesPage from './pages/nodes/NodesPage'
import AgentsPage from './pages/agents/AgentsPage'
import UsersPage from './pages/users/UsersPage'
import TransactionsPage from './pages/transactions/TransactionsPage'
import OrdersPage from './pages/orders/OrdersPage'
import MatchingPage from './pages/matching/MatchingPage'
import GeneCapsulesPage from './pages/gene-capsules/GeneCapsulesPage'
import IntelligencePage from './pages/intelligence/IntelligencePage'
import GovernancePage from './pages/governance/GovernancePage'
import ContractsOverviewPage from './pages/contracts/ContractsOverviewPage'
import StakingPage from './pages/contracts/StakingPage'
import RewardsPage from './pages/contracts/RewardsPage'
import GovernanceContractsPage from './pages/contracts/GovernanceContractsPage'
import MarketPage from './pages/contracts/MarketPage'
import OrdersContractsPage from './pages/contracts/OrdersContractsPage'
import SystemPage from './pages/system/SystemPage'
import HealthPage from './pages/system/HealthPage'
import ConfigPage from './pages/system/ConfigPage'
import LogsPage from './pages/system/LogsPage'
import PermissionsPage from './pages/permissions/PermissionsPage'

const ADMIN_ROLES = ['superadmin', 'node_admin']

function AdminRoute({ children }: { children: React.ReactNode }) {
  const userRole = useAuthStore(s => s.userRole)
  const isConnected = useAuthStore(s => s.isConnected)
  const address = useAuthStore(s => s.address)

  if (!isConnected || !address) {
    return <Navigate to="/login" replace />
  }
  if (!ADMIN_ROLES.includes(userRole)) {
    return <Navigate to="/403" replace />
  }

  return <>{children}</>
}

// 根据路径渲染对应的页面组件
function AdminPageRouter() {
  const location = useLocation()
  const path = location.pathname.replace('/admin', '') || '/'

  switch (path) {
    case '/':
    case '/dashboard':
      return <DashboardPage />
    case '/nodes':
      return <NodesPage />
    case '/agents':
      return <AgentsPage />
    case '/users':
      return <UsersPage />
    case '/transactions':
      return <TransactionsPage />
    case '/orders':
      return <OrdersPage />
    case '/matching':
      return <MatchingPage />
    case '/gene-capsules':
      return <GeneCapsulesPage />
    case '/intelligence':
      return <IntelligencePage />
    case '/governance':
      return <GovernancePage />
    case '/contracts':
      return <ContractsOverviewPage />
    case '/contracts/staking':
      return <StakingPage />
    case '/contracts/rewards':
      return <RewardsPage />
    case '/contracts/governance':
      return <GovernanceContractsPage />
    case '/contracts/market':
      return <MarketPage />
    case '/contracts/orders':
      return <OrdersContractsPage />
    case '/system':
      return <SystemPage />
    case '/system/health':
      return <HealthPage />
    case '/system/config':
      return <ConfigPage />
    case '/system/logs':
      return <LogsPage />
    case '/permissions':
      return <PermissionsPage />
    default:
      return <DashboardPage />
  }
}

export default function AdminApp() {
  return (
    <AdminRoute>
      <AdminLayout>
        <AdminPageRouter />
      </AdminLayout>
    </AdminRoute>
  )
}
