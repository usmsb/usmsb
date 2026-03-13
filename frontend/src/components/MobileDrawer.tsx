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
  Bot,
  Presentation,
  Dna,
  FileCode,
  Home,
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
  const isDark = theme === 'dark'

  const logoSrc = isDark ? '/logo-dark.svg' : '/logo.svg'

  const mainNav = [
    { name: t('nav.dashboard'), href: '/app/dashboard', icon: LayoutDashboard },
    { name: t('nav.agents'), href: '/app/agents', icon: Users },
    { name: t('nav.metaAgent'), href: '/app/chat', icon: Bot },
    { name: t('nav.matching'), href: '/app/matching', icon: Zap },
    { name: t('nav.network'), href: '/app/network', icon: Network },
  ]

  const toolsNav = [
    { name: t('nav.collaborations'), href: '/app/collaborations', icon: GitBranch },
    { name: t('nav.simulations'), href: '/app/simulations', icon: FlaskConical },
    { name: t('nav.analytics'), href: '/app/analytics', icon: BarChart3 },
    { name: t('nav.marketplace'), href: '/app/marketplace', icon: Store },
    { name: t('nav.governance'), href: '/app/governance', icon: Scale },
    { name: t('nav.geneCapsule'), href: '/app/gene-capsule/explore', icon: Dna },
    { name: t('nav.contracts'), href: '/app/contracts', icon: FileCode },
  ]

  const quickActions = [
    { name: t('sidebar.publishService'), href: '/app/publish/service', icon: PlusCircle, color: 'blue', desc: t('sidebar.publishServiceDesc') },
    { name: t('sidebar.publishDemand'), href: '/app/publish/demand', icon: Target, color: 'purple', desc: t('sidebar.publishDemandDesc') },
    { name: t('sidebar.investorPresentation'), href: '/pitch', icon: Presentation, color: 'green', desc: t('sidebar.vibeIntroduction') },
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
          'fixed left-0 top-0 h-full w-80 max-w-[85vw] z-50 transform transition-transform duration-300 ease-in-out md:hidden',
          'flex flex-col',
          isDark ? 'bg-cyber-card border-r border-neon-blue/20' : 'bg-white border-r border-gray-200',
          isOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Neon glow effect - Dark mode */}
        {isDark && (
          <div className="absolute top-0 right-0 bottom-0 w-px bg-gradient-to-b from-transparent via-neon-blue/30 to-transparent" />
        )}

        {/* Header */}
        <div className={clsx(
          'h-16 flex items-center justify-between px-4 shrink-0 border-b',
          isDark ? 'border-neon-blue/20' : 'border-gray-200'
        )}>
          <Link to="/" onClick={onClose} className="flex items-center gap-3 group">
            <img
              src={logoSrc}
              alt="USMSB Logo"
              className={clsx(
                'w-8 h-8 transition-all duration-300 group-hover:scale-110',
                isDark && 'group-hover:shadow-[0_0_15px_rgba(59,130,246,0.5)]'
              )}
            />
            <div className="flex flex-col">
              <span className={clsx(
                'font-bold text-lg leading-tight',
                isDark ? 'font-cyber bg-gradient-to-r from-neon-blue via-neon-purple to-neon-green bg-clip-text text-transparent' : 'text-gray-900'
              )}>USMSB</span>
              <span className={clsx('text-xs', isDark ? 'text-neon-blue/60' : 'text-gray-500')}>SDK Platform</span>
            </div>
          </Link>
          <button
            onClick={onClose}
            className={clsx(
              'p-2 rounded-lg transition-colors',
              isDark ? 'hover:bg-neon-blue/10 text-neon-blue/70 hover:text-neon-blue' : 'hover:bg-gray-100 text-gray-500'
            )}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        {/* Main Content - Scrollable */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-4 space-y-4">
            {/* Main Navigation */}
            <div>
              <p className={clsx(
                'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
                isDark ? 'text-neon-blue/60 font-cyber' : 'text-gray-500'
              )}>Main</p>
              {mainNav.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  onClick={handleNavClick}
                  className={({ isActive }) => clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                    !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                    !isActive && isDark && 'text-gray-300 hover:text-neon-blue',
                    isActive && !isDark && 'bg-gradient-to-r from-blue-50 to-purple-50 text-blue-700 font-medium border border-blue-200',
                    isActive && isDark && 'bg-gradient-to-r from-neon-blue/20 to-neon-purple/20 text-neon-blue font-cyber border border-neon-blue/40 shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                  )}
                >
                  {({ isActive }) => (
                    <>
                      <item.icon size={20} className={clsx(
                        'shrink-0', isActive ? (isDark ? 'text-neon-blue' : 'text-blue-600') : (isDark ? 'text-gray-400' : 'text-gray-500')
                      )} />
                      <span className={clsx('font-medium', isActive && isDark && 'font-cyber')}>{item.name}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>

            {/* Tools Navigation */}
            <div>
              <p className={clsx(
                'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
                isDark ? 'text-neon-purple/60 font-cyber' : 'text-gray-500'
              )}>Tools</p>
              {toolsNav.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.href}
                  onClick={handleNavClick}
                  className={({ isActive }) => clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                    !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                    !isActive && isDark && 'text-gray-300 hover:text-neon-purple',
                    isActive && !isDark && 'bg-gradient-to-r from-purple-50 to-pink-50 text-purple-700 font-medium border border-purple-200',
                    isActive && isDark && 'bg-gradient-to-r from-neon-purple/20 to-pink-500/20 text-neon-purple font-cyber border border-neon-purple/40 shadow-[0_0_15px_rgba(191,0,255,0.2)]'
                  )}
                >
                  {({ isActive }) => (
                    <>
                      <item.icon size={20} className={clsx(
                        'shrink-0', isActive ? (isDark ? 'text-neon-purple' : 'text-purple-600') : (isDark ? 'text-gray-400' : 'text-gray-500')
                      )} />
                      <span className={clsx('font-medium', isActive && isDark && 'font-cyber')}>{item.name}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>

            {/* Quick Actions */}
            <div className={clsx(
              'pt-4 border-t',
              isDark ? 'border-neon-green/20' : 'border-gray-200'
            )}>
              <p className={clsx(
                'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
                isDark ? 'text-neon-green/60 font-cyber' : 'text-gray-500'
              )}>{t('sidebar.quickActions')}</p>
              <div className={clsx(
                'rounded-xl p-2 space-y-1',
                isDark ? 'bg-gradient-to-br from-cyber-card to-cyber-dark border border-neon-green/20' : 'bg-gray-50 border border-gray-100'
              )}>
                {quickActions.map((action) => (
                  <NavLink
                    key={action.name}
                    to={action.href}
                    onClick={handleNavClick}
                    className={({ isActive }) => clsx(
                      'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                      !isActive && !isDark && 'text-gray-600 hover:bg-white hover:shadow-sm',
                      !isActive && isDark && 'text-gray-300',
                      isActive && !isDark && action.color === 'blue' && 'bg-blue-100 text-blue-700',
                      isActive && !isDark && action.color === 'purple' && 'bg-purple-100 text-purple-700',
                      isActive && !isDark && action.color === 'green' && 'bg-green-100 text-green-700',
                      isActive && isDark && action.color === 'blue' && 'bg-neon-blue/15 text-neon-blue border border-neon-blue/40',
                      isActive && isDark && action.color === 'purple' && 'bg-neon-purple/15 text-neon-purple border border-neon-purple/40',
                      isActive && isDark && action.color === 'green' && 'bg-neon-green/15 text-neon-green border border-neon-green/40'
                    )}
                  >
                    {({ isActive }) => (
                      <>
                        <div className={clsx('p-1.5 rounded-md', isDark && action.color === 'blue' && 'bg-neon-blue/20', isDark && action.color === 'purple' && 'bg-neon-purple/20', isDark && action.color === 'green' && 'bg-neon-green/20')}>
                          <action.icon size={16} className={clsx(
                            isDark && action.color === 'blue' && 'text-neon-blue',
                            isDark && action.color === 'purple' && 'text-neon-purple',
                            isDark && action.color === 'green' && 'text-neon-green',
                            !isDark && action.color === 'blue' && 'text-blue-600',
                            !isDark && action.color === 'purple' && 'text-purple-600',
                            !isDark && action.color === 'green' && 'text-green-600'
                          )} />
                        </div>
                        <div className="flex flex-col">
                          <span className={clsx('text-sm font-medium', isActive && isDark && 'font-cyber')}>{action.name}</span>
                          <span className={clsx('text-xs', isDark ? 'text-gray-500' : 'text-gray-500')}>{action.desc}</span>
                        </div>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Section - Fixed */}
        <div className={clsx(
          'shrink-0 p-4 border-t',
          isDark ? 'border-neon-blue/20 bg-cyber-card/80' : 'border-gray-200 bg-white'
        )}>
          <NavLink
            to="/app/settings"
            onClick={handleNavClick}
            className={({ isActive }) => clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
              !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
              !isActive && isDark && 'text-gray-300 hover:text-neon-blue',
              isActive && !isDark && 'bg-gray-100 text-gray-900 font-medium',
              isActive && isDark && 'bg-gradient-to-r from-neon-blue/20 to-cyan-500/20 text-neon-blue font-cyber border border-neon-blue/40'
            )}
          >
            {({ isActive }) => (
              <>
                <Settings size={20} className={isActive && isDark ? 'text-neon-blue' : ''} />
                <span className="font-medium">{t('nav.settings')}</span>
              </>
            )}
          </NavLink>
          <Link
            to="/"
            onClick={onClose}
            className={clsx(
              'flex items-center gap-3 px-3 py-2.5 mt-2 rounded-lg transition-all duration-200',
              isDark ? 'text-gray-500 hover:text-neon-green hover:bg-neon-green/5' : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            )}
          >
            <Home size={18} />
            <span className="text-sm">Back to Home</span>
          </Link>
        </div>
      </div>
    </>
  )
}
