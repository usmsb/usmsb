import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Cpu, Boxes, FileText, DollarSign, Users, Radio, Settings } from 'lucide-react'
import clsx from 'clsx'

const schedulerLinks = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/nodes', icon: Cpu, label: 'GPU Nodes' },
  { to: '/models', icon: Boxes, label: 'Models' },
  { to: '/requests', icon: FileText, label: 'Requests' },
  { to: '/revenue', icon: DollarSign, label: 'Revenue' },
  { to: '/users', icon: Users, label: 'Users' },
  { to: '/monitor', icon: Radio, label: 'Monitor' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="desktop-sidebar">
      <div className="p-6 border-b border-cyber-border">
        <h1 className="font-orbitron text-lg font-bold gradient-text tracking-wider">
          USMSB DIST
        </h1>
        <p className="text-xs text-text-secondary mt-1 font-mono">Distributed Inference</p>
      </div>
      <nav className="flex-1 p-4 space-y-1">
        {schedulerLinks.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-rajdhani font-medium transition-all duration-200',
                isActive
                  ? 'bg-neon-blue/10 text-neon-blue border border-neon-blue/30'
                  : 'text-text-secondary hover:text-neon-blue hover:bg-neon-blue/5'
              )
            }
          >
            <Icon size={18} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
