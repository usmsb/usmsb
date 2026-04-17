import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'
import TopBar from './TopBar'

interface Props {
  variant?: 'scheduler' | 'executor'
}

export default function AppShell({ variant = 'scheduler' }: Props) {
  return (
    <div className="app-shell cyber-grid-bg">
      <Sidebar />
      <main className="app-main">
        <TopBar />
        <div className="app-content">
          <Outlet />
        </div>
      </main>
      <MobileTabBar />
    </div>
  )
}
