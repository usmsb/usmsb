import { Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import AppShell from '@/components/layout/AppShell'
import LoginPage from '@/pages/auth/LoginPage'
import DashboardPage from '@/pages/scheduler/DashboardPage'
import NodesPage from '@/pages/scheduler/NodesPage'
import NodeDetailPage from '@/pages/scheduler/NodeDetailPage'
import ModelsPage from '@/pages/scheduler/ModelsPage'
import RequestsPage from '@/pages/scheduler/RequestsPage'
import RequestDetailPage from '@/pages/scheduler/RequestDetailPage'
import RevenuePage from '@/pages/scheduler/RevenuePage'
import UsersPage from '@/pages/scheduler/UsersPage'
import UserDetailPage from '@/pages/scheduler/UserDetailPage'
import MonitorPage from '@/pages/scheduler/MonitorPage'
import SettingsPage from '@/pages/scheduler/SettingsPage'
import NodeDashboardPage from '@/pages/executor/NodeDashboardPage'
import NodeRevenuePage from '@/pages/executor/NodeRevenuePage'
import NodeModelsPage from '@/pages/executor/NodeModelsPage'
import NodeHistoryPage from '@/pages/executor/NodeHistoryPage'
import NodeSettingsPage from '@/pages/executor/NodeSettingsPage'

function App() {
  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#0d0d14',
            color: '#e0e0ff',
            border: '1px solid #1a1a2e',
            fontFamily: 'Rajdhani, sans-serif',
          },
        }}
      />
      <Routes>
        {/* Auth */}
        <Route path="/login" element={<LoginPage />} />

        {/* Node Executor routes */}
        <Route path="/node" element={<AppShell variant="executor" />}>
          <Route index element={<NodeDashboardPage />} />
          <Route path="revenue" element={<NodeRevenuePage />} />
          <Route path="models" element={<NodeModelsPage />} />
          <Route path="history" element={<NodeHistoryPage />} />
          <Route path="settings" element={<NodeSettingsPage />} />
        </Route>

        {/* Global Scheduler routes */}
        <Route path="/" element={<AppShell variant="scheduler" />}>
          <Route index element={<DashboardPage />} />
          <Route path="nodes" element={<NodesPage />} />
          <Route path="nodes/:nodeId" element={<NodeDetailPage />} />
          <Route path="models" element={<ModelsPage />} />
          <Route path="requests" element={<RequestsPage />} />
          <Route path="requests/:id" element={<RequestDetailPage />} />
          <Route path="revenue" element={<RevenuePage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="users/:wallet" element={<UserDetailPage />} />
          <Route path="monitor" element={<MonitorPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}

export default App
