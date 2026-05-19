/**
 * Admin Panel App Router
 * 管理员专用管理后台路由
 */
import { Routes, Route, Navigate } from 'react-router-dom'
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

export default function AdminApp() {
  return (
    <AdminRoute>
      <Routes>
        {/* 入口重定向 */}
        <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />

        {/* 主要页面 */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="nodes" element={<NodesPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="matching" element={<MatchingPage />} />
          <Route path="gene-capsules" element={<GeneCapsulesPage />} />
          <Route path="intelligence" element={<IntelligencePage />} />
          <Route path="governance" element={<GovernancePage />} />

          {/* 合约子页面 */}
          <Route path="contracts" element={<ContractsOverviewPage />} />
          <Route path="contracts/staking" element={<StakingPage />} />
          <Route path="contracts/rewards" element={<RewardsPage />} />
          <Route path="contracts/governance" element={<GovernanceContractsPage />} />
          <Route path="contracts/market" element={<MarketPage />} />
          <Route path="contracts/orders" element={<OrdersContractsPage />} />

          {/* 系统管理 */}
          <Route path="system" element={<SystemPage />} />
          <Route path="system/health" element={<HealthPage />} />
          <Route path="system/config" element={<ConfigPage />} />
          <Route path="system/logs" element={<LogsPage />} />

          {/* 权限管理（仅 superadmin） */}
          <Route path="permissions" element={<PermissionsPage />} />
        </Route>

        {/* 独立全屏路由 */}
        <Route path="/admin/command-center" element={<CommandCenterPage />} />
      </Routes>
    </AdminRoute>
  )
}
