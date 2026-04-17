import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Cpu, DollarSign, Settings } from 'lucide-react'
import clsx from 'clsx'

const tabs = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/nodes', icon: Cpu, label: 'Nodes' },
  { to: '/revenue', icon: DollarSign, label: 'Revenue' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function MobileTabBar() {
  const location = useLocation()
  return (
    <nav className="mobile-tab-bar">
      {tabs.map(({ to, icon: Icon, label }) => {
        const isActive = to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
        return (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={clsx(
              'flex flex-col items-center gap-1 py-2 px-4 rounded-lg transition-colors',
              isActive ? 'text-neon-blue' : 'text-text-secondary'
            )}
          >
            <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
            <span className="text-xs font-rajdhani font-medium">{label}</span>
          </NavLink>
        )
      })}
    </nav>
  )
}
