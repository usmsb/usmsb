import { Routes, Route, Navigate } from 'react-router-dom'
import { ReactNode, useState, useEffect } from 'react'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import Dashboard from './pages/Dashboard'
import Agents from './pages/Agents'
import AgentDetail from './pages/AgentDetail'
import RegisterAgent from './pages/RegisterAgent'
import ActiveMatching from './pages/ActiveMatching'
import NetworkExplorer from './pages/NetworkExplorer'
import Collaborations from './pages/Collaborations'
import Simulations from './pages/Simulations'
import Analytics from './pages/Analytics'
import Marketplace from './pages/Marketplace'
import Governance from './pages/Governance'
import Settings from './pages/Settings'
import Onboarding from './pages/Onboarding'
import PublishService from './pages/PublishService'
import PublishDemand from './pages/PublishDemand'
import LandingPage from './pages/LandingPage'
import DocsPage from './pages/DocsPage'
import LegalPage from './pages/LegalPage'
import Chat from './pages/Chat'
import PitchPage from './pages/pitch'
import { useAuthStore } from './stores/authStore'
import { StakeGuideModal } from './components/StakeGuideModal'

// Protected Route Component that requires staking
function StakeProtectedRoute({
  children,
  featureName,
}: {
  children: ReactNode
  featureName: string
}) {
  const { stakeStatus, stakeRequired, accessToken } = useAuthStore()
  const [showGuideModal, setShowGuideModal] = useState(false)
  
  // Check access in useEffect to avoid infinite loops
  useEffect(() => {
    if (stakeRequired && accessToken && stakeStatus !== 'staked') {
      setShowGuideModal(true)
    }
  }, [stakeRequired, accessToken, stakeStatus])

  const handleCloseModal = () => {
    setShowGuideModal(false)
  }

  // Always render children - modal is shown conditionally via useEffect
  return (
    <>
      {children}
      {showGuideModal && (
        <StakeGuideModal
          isOpen={showGuideModal}
          onClose={handleCloseModal}
          featureName={featureName}
        />
      )}
    </>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Landing Page - root path */}
        <Route path="/" element={<LandingPage />} />

        {/* Docs Page - full page without layout */}
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/docs/:docId" element={<DocsPage />} />

        {/* Legal Pages - full page without layout */}
        <Route path="/legal/:type" element={<LegalPage />} />

        {/* Pitch Page - Investor Presentation */}
        <Route path="/pitch" element={<PitchPage />} />

        {/* Onboarding - outside Layout */}
        <Route path="/app/onboarding" element={<Onboarding />} />

        {/* Main App - with Layout, all under /app */}
        <Route path="/app" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="agents" element={<Agents />} />
          <Route
            path="agents/register"
            element={
              <StakeProtectedRoute featureName="Register Agent">
                <RegisterAgent />
              </StakeProtectedRoute>
            }
          />
          <Route path="agents/:id" element={<AgentDetail />} />
          <Route
            path="matching"
            element={
              <StakeProtectedRoute featureName="Matching">
                <ActiveMatching />
              </StakeProtectedRoute>
            }
          />
          <Route path="network" element={<NetworkExplorer />} />
          <Route
            path="collaborations"
            element={
              <StakeProtectedRoute featureName="Collaborations">
                <Collaborations />
              </StakeProtectedRoute>
            }
          />
          <Route path="simulations" element={<Simulations />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="marketplace" element={<Marketplace />} />
          <Route
            path="governance"
            element={
              <StakeProtectedRoute featureName="Governance">
                <Governance />
              </StakeProtectedRoute>
            }
          />
          <Route path="chat" element={<Chat />} />
          <Route path="settings" element={<Settings />} />

          {/* User Actions */}
          <Route
            path="publish/service"
            element={
              <StakeProtectedRoute featureName="Publish Service">
                <PublishService />
              </StakeProtectedRoute>
            }
          />
          <Route
            path="publish/demand"
            element={
              <StakeProtectedRoute featureName="Publish Demand">
                <PublishDemand />
              </StakeProtectedRoute>
            }
          />
        </Route>

        {/* Redirect old routes to new locations for backwards compatibility */}
        <Route path="/landing" element={<Navigate to="/" replace />} />
        <Route path="/onboarding" element={<Navigate to="/app/onboarding" replace />} />
        <Route path="/agents" element={<Navigate to="/app/agents" replace />} />
        <Route path="/agents/register" element={<Navigate to="/app/agents/register" replace />} />
        <Route path="/agents/:id" element={<Navigate to="/app/agents/:id" replace />} />
        <Route path="/dashboard" element={<Navigate to="/app/dashboard" replace />} />
        <Route path="/matching" element={<Navigate to="/app/matching" replace />} />
        <Route path="/network" element={<Navigate to="/app/network" replace />} />
        <Route path="/collaborations" element={<Navigate to="/app/collaborations" replace />} />
        <Route path="/simulations" element={<Navigate to="/app/simulations" replace />} />
        <Route path="/analytics" element={<Navigate to="/app/analytics" replace />} />
        <Route path="/marketplace" element={<Navigate to="/app/marketplace" replace />} />
        <Route path="/governance" element={<Navigate to="/app/governance" replace />} />
        <Route path="/chat" element={<Navigate to="/app/chat" replace />} />
        <Route path="/settings" element={<Navigate to="/app/settings" replace />} />
        <Route path="/publish/service" element={<Navigate to="/app/publish/service" replace />} />
        <Route path="/publish/demand" element={<Navigate to="/app/publish/demand" replace />} />

        {/* Catch-all redirect to dashboard */}
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Routes>
    </ErrorBoundary>
  )
}

export default App
