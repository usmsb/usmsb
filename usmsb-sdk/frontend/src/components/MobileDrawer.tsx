import { NavLink, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  LayoutDashboard,
  Users,
  FlaskConical,
  BarChart3,
  Store,
  Scale,
  Settings,
  X,
  Zap,
  Network,
  GitBranch,
  PlusCircle,
  Target,
} from 'lucide-react'
import { useAppStore } from '@/store'
import clsx from 'clsx'

interface MobileDrawerProps {
  isOpen: boolean
  onClose: () => void
}

export default function MobileDrawer({ isOpen, onClose }: MobileDrawerProps) {
  const { t } = useTranslation()
  const { theme } = useAppStore()

  // Logo source based on theme
  const logoSrc = theme === 'dark' ? '/logo-dark.svg' : '/logo.svg'

  const navigation = [
    { name: t('nav.dashboard'), href: '/app/dashboard', icon: LayoutDashboard },
    { name: t('nav.agents'), href: '/app/agents', icon: Users },
    { name: t('nav.matching'), href: '/app/matching', icon: Zap },
    { name: t('nav.network'), href: '/app/network', icon: Network },
    { name: t('nav.collaborations'), href: '/app/collaborations', icon: GitBranch },
    { name: t('nav.simulations'), href: '/app/simulations', icon: FlaskConical },
    { name: t('nav.analytics'), href: '/app/analytics', icon: BarChart3 },
    { name: t('nav.marketplace'), href: '/app/marketplace', icon: Store },
    { name: t('nav.governance'), href: '/app/governance', icon: Scale },
  ]

  const quickActions = [
    { name: t('sidebar.publishService'), href: '/app/publish/service', icon: PlusCircle, color: 'text-green-600 dark:text-green-400', desc: t('sidebar.publishServiceDesc') },
    { name: t('sidebar.publishDemand'), href: '/app/publish/demand', icon: Target, color: 'text-blue-600 dark:text-blue-400', desc: t('sidebar.publishDemandDesc') },
  ]

  const handleNavClick = () => {
    onClose()
  }

  return (
    <>
      {/* Backdrop */}
      <div
        className={clsx(
          'fixed inset-0 bg-black/50 z-40 transition-opacity duration-300 md:hidden',
          isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <div
        className={clsx(
          'fixed left-0 top-0 h-full w-72 z-50 transform transition-transform duration-300 ease-in-out md:hidden',
          'bg-white dark:bg-secondary-900',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-secondary-200 dark:border-secondary-700">
          <Link
            to="/"
            onClick={onClose}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <img
              src={logoSrc}
              alt="USMSB SDK Logo"
              className="w-8 h-8"
            />
            <span className="font-semibold text-secondary-900 dark:text-secondary-100">USMSB SDK</span>
          </Link>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-800 text-secondary-500 dark:text-secondary-400"
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1 overflow-y-auto h-[calc(100%-8rem)]">
          {navigation.map((item) => (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={handleNavClick}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                    : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-800'
                )
              }
            >
              <item.icon size={20} />
              <span className="font-medium">{item.name}</span>
            </NavLink>
          ))}

          {/* Quick Actions */}
          <div className="pt-4 mt-4 border-t border-secondary-200 dark:border-secondary-700">
            <p className="text-xs font-medium text-secondary-400 dark:text-secondary-500 uppercase tracking-wider mb-2 px-3">
              {t('sidebar.quickActions') || 'Quick Actions'}
            </p>
            <div className="space-y-1">
              {quickActions.map((action) => (
                <NavLink
                  key={action.name}
                  to={action.href}
                  onClick={handleNavClick}
                  className={({ isActive }) =>
                    clsx(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                      isActive
                        ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                        : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-800'
                    )
                  }
                >
                  <action.icon size={18} className={action.color} />
                  <div className="flex flex-col">
                    <span className="text-sm font-medium">{action.name}</span>
                    <span className="text-xs text-secondary-400 dark:text-secondary-500">{action.desc}</span>
                  </div>
                </NavLink>
              ))}
            </div>
          </div>
        </nav>

        {/* Bottom section */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-secondary-200 dark:border-secondary-700 bg-white dark:bg-secondary-900">
          <NavLink
            to="/app/settings"
            onClick={handleNavClick}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400'
                  : 'text-secondary-600 dark:text-secondary-400 hover:bg-secondary-100 dark:hover:bg-secondary-800'
              )
            }
          >
            <Settings size={20} />
            <span className="font-medium">{t('nav.settings')}</span>
          </NavLink>
        </div>
      </div>
    </>
  )
}
