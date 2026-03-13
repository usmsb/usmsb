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
  ChevronLeft,
  ChevronRight,
  Zap,
  Network,
  GitBranch,
  PlusCircle,
  Target,
  Home,
  Bot,
  Presentation,
  Dna,
  FileCode,
} from 'lucide-react'
import { useAppStore } from '@/store'
import { useState } from 'react'
import clsx from 'clsx'

export default function Sidebar() {
  const { t } = useTranslation()
  const { sidebarOpen, setSidebarOpen, theme } = useAppStore()
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  const isDark = theme === 'dark'

  // Logo source based on theme
  const logoSrc = isDark ? '/logo-dark.svg' : '/logo.svg'

  const navigation = [
    { name: t('nav.dashboard'), href: '/app/dashboard', icon: LayoutDashboard, group: 'main' },
    { name: t('nav.agents'), href: '/app/agents', icon: Users, group: 'main' },
    { name: t('nav.metaAgent'), href: '/app/chat', icon: Bot, group: 'main' },
    { name: t('nav.matching'), href: '/app/matching', icon: Zap, group: 'main' },
    { name: t('nav.network'), href: '/app/network', icon: Network, group: 'main' },
    { name: t('nav.collaborations'), href: '/app/collaborations', icon: GitBranch, group: 'tools' },
    { name: t('nav.simulations'), href: '/app/simulations', icon: FlaskConical, group: 'tools' },
    { name: t('nav.analytics'), href: '/app/analytics', icon: BarChart3, group: 'tools' },
    { name: t('nav.marketplace'), href: '/app/marketplace', icon: Store, group: 'tools' },
    { name: t('nav.governance'), href: '/app/governance', icon: Scale, group: 'tools' },
    { name: t('nav.geneCapsule'), href: '/app/gene-capsule/explore', icon: Dna, group: 'tools' },
    { name: t('nav.contracts', 'Contracts'), href: '/app/contracts', icon: FileCode, group: 'tools' },
  ]

  const quickActions = [
    { name: t('sidebar.publishService'), href: '/app/publish/service', icon: PlusCircle, desc: t('sidebar.publishServiceDesc'), color: 'blue' },
    { name: t('sidebar.publishDemand'), href: '/app/publish/demand', icon: Target, desc: t('sidebar.publishDemandDesc'), color: 'purple' },
    { name: t('sidebar.investorPresentation'), href: '/pitch', icon: Presentation, desc: t('sidebar.vibeIntroduction'), color: 'green' },
  ]

  // Group navigation items
  const mainNav = navigation.filter(item => item.group === 'main')
  const toolsNav = navigation.filter(item => item.group === 'tools')

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 h-full transition-all duration-300 ease-out z-30',
        'flex flex-col',
        // Light Mode
        'bg-white border-r border-gray-200',
        // Dark Mode - Cyberpunk card style
        isDark && 'bg-cyber-card/95 backdrop-blur-xl border-r border-neon-blue/20',
        sidebarOpen ? 'w-64' : 'w-20'
      )}
    >
      {/* Dark mode neon glow border - Left side */}
      {isDark && (
        <div className="absolute top-0 left-0 bottom-0 w-px bg-gradient-to-b from-transparent via-neon-blue/40 to-transparent pointer-events-none" />
      )}

      {/* ========================================
          LOGO SECTION
          ======================================== */}
      <div className={clsx(
        'h-16 flex items-center justify-between px-4 shrink-0',
        'border-b',
        isDark ? 'border-neon-blue/20' : 'border-gray-200'
      )}>
        {sidebarOpen ? (
          <Link to="/" className="flex items-center gap-3 group">
            <div className={clsx('relative', isDark && 'pulse-ring rounded-full')}>
              <img
                src={logoSrc}
                alt="USMSB Logo"
                className={clsx(
                  'w-9 h-9 transition-all duration-300',
                  'group-hover:scale-110',
                  isDark && 'group-hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]'
                )}
              />
            </div>
            <div className="flex flex-col">
              <span className={clsx(
                'font-bold text-lg leading-tight transition-colors',
                isDark
                  ? 'font-cyber bg-gradient-to-r from-neon-blue via-neon-purple to-neon-green bg-clip-text text-transparent group-hover:from-neon-green group-hover:to-neon-blue'
                  : 'text-gray-900 group-hover:text-blue-600'
              )}>USMSB</span>
              <span className={clsx(
                'text-xs',
                isDark ? 'text-neon-blue/60' : 'text-gray-500'
              )}>SDK Platform</span>
            </div>
          </Link>
        ) : (
          <Link to="/" className="flex items-center justify-center w-full group">
            <div className={clsx('relative', isDark && 'pulse-ring rounded-full')}>
              <img
                src={logoSrc}
                alt="USMSB Logo"
                className={clsx(
                  'w-9 h-9 transition-all duration-300',
                  'group-hover:scale-110',
                  isDark && 'group-hover:shadow-[0_0_20px_rgba(59,130,246,0.5)]'
                )}
              />
            </div>
          </Link>
        )}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-expanded={sidebarOpen}
          aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          className={clsx(
            'p-2 rounded-lg transition-all duration-200',
            'active:scale-95',
            isDark
              ? 'text-neon-blue/70 hover:text-neon-blue hover:bg-neon-blue/10'
              : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100',
            !sidebarOpen && 'absolute right-2'
          )}
        >
          {sidebarOpen ? <ChevronLeft size={20} /> : <ChevronRight size={20} />}
        </button>
      </div>

      {/* ========================================
          NAVIGATION CONTENT - Scrollable
          ======================================== */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-4">
        {/* Main Navigation */}
        <nav className="px-3 space-y-1" aria-label="Main navigation">
          {sidebarOpen && (
            <p className={clsx(
              'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
              isDark ? 'text-neon-blue/60 font-cyber' : 'text-gray-500'
            )}>
              Main
            </p>
          )}
          {mainNav.map((item, index) => (
            <NavLink
              key={item.name}
              to={item.href}
              onMouseEnter={() => setHoveredItem(item.name)}
              onMouseLeave={() => setHoveredItem(null)}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                'group relative',
                // Base
                !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                !isActive && isDark && 'text-gray-300 hover:text-neon-blue',
                // Light mode active
                isActive && !isDark && 'bg-gradient-to-r from-blue-50 to-purple-50 text-blue-700 font-medium border border-blue-200',
                // Dark mode active - Cyberpunk glow effect
                isActive && isDark && [
                  'bg-gradient-to-r from-neon-blue/20 to-neon-purple/20',
                  'text-neon-blue font-cyber',
                  'border border-neon-blue/40',
                  'shadow-[0_0_15px_rgba(0,245,255,0.3)]',
                ],
                !sidebarOpen && 'justify-center',
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    size={20}
                    className={clsx(
                      'shrink-0 transition-all duration-200',
                      isActive
                        ? isDark ? 'text-neon-blue drop-shadow-[0_0_8px_rgba(0,245,255,0.8)]' : 'text-blue-600'
                        : isDark ? 'text-gray-400 group-hover:text-neon-blue' : 'text-gray-500 group-hover:text-gray-700'
                    )}
                  />
                  {sidebarOpen && (
                    <span className={clsx(
                      'truncate transition-all',
                      isActive && 'font-medium',
                      isDark && 'tracking-wide group-hover:text-neon-blue'
                    )}>{item.name}</span>
                  )}
                  {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={clsx(
                      'absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50',
                      'animate-fade-in',
                      isDark
                        ? 'bg-cyber-card border border-neon-blue/40 text-neon-blue shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                        : 'bg-white text-gray-900 shadow-lg border border-gray-200'
                    )}>
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Tools Section */}
        <nav className="px-3 mt-6 space-y-1" aria-label="Tools navigation">
          {sidebarOpen && (
            <p className={clsx(
              'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
              isDark ? 'text-neon-purple/60 font-cyber' : 'text-gray-500'
            )}>
              Tools
            </p>
          )}
          {toolsNav.map((item, index) => (
            <NavLink
              key={item.name}
              to={item.href}
              onMouseEnter={() => setHoveredItem(item.name)}
              onMouseLeave={() => setHoveredItem(null)}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
                'group relative',
                // Base
                !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
                !isActive && isDark && 'text-gray-300 hover:text-neon-purple',
                // Light mode active
                isActive && !isDark && 'bg-gradient-to-r from-purple-50 to-pink-50 text-purple-700 font-medium border border-purple-200',
                // Dark mode active - Cyberpunk purple glow
                isActive && isDark && [
                  'bg-gradient-to-r from-neon-purple/20 to-pink-500/20',
                  'text-neon-purple font-cyber',
                  'border border-neon-purple/40',
                  'shadow-[0_0_15px_rgba(191,0,255,0.3)]',
                ],
                !sidebarOpen && 'justify-center',
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon
                    size={20}
                    className={clsx(
                      'shrink-0 transition-all duration-200',
                      isActive
                        ? isDark ? 'text-neon-purple drop-shadow-[0_0_8px_rgba(191,0,255,0.8)]' : 'text-purple-600'
                        : isDark ? 'text-gray-400 group-hover:text-neon-purple' : 'text-gray-500 group-hover:text-gray-700'
                    )}
                  />
                  {sidebarOpen && (
                    <span className={clsx(
                      'truncate transition-all',
                      isActive && 'font-medium',
                      isDark && 'tracking-wide group-hover:text-neon-purple'
                    )}>{item.name}</span>
                  )}
                  {/* Hover tooltip when collapsed */}
                  {!sidebarOpen && hoveredItem === item.name && (
                    <div className={clsx(
                      'absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50',
                      'animate-fade-in',
                      isDark
                        ? 'bg-cyber-card border border-neon-purple/40 text-neon-purple shadow-[0_0_15px_rgba(191,0,255,0.2)]'
                        : 'bg-white text-gray-900 shadow-lg border border-gray-200'
                    )}>
                      {item.name}
                    </div>
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Quick Actions */}
        {sidebarOpen && (
          <div className="px-3 mt-6">
            <p className={clsx(
              'px-3 text-xs font-semibold uppercase tracking-wider mb-2',
              isDark ? 'text-neon-green/60 font-cyber' : 'text-gray-500'
            )}>
              {t('sidebar.quickActions')}
            </p>
            {/* Quick Actions Card Container */}
            <div className={clsx(
              'rounded-xl p-3 space-y-2',
              isDark
                ? 'bg-gradient-to-br from-cyber-card to-cyber-dark border border-neon-green/20'
                : 'bg-gray-50 border border-gray-100'
            )}>
              {quickActions.map((action) => (
                <NavLink
                  key={action.name}
                  to={action.href}
                  className={({ isActive }) => clsx(
                    'flex items-center gap-3 px-3 py-3 rounded-lg transition-all duration-200',
                    'group relative overflow-hidden',
                    // Base states
                    !isDark && 'text-gray-600 hover:bg-white hover:shadow-md',
                    isDark && 'text-gray-300 hover:text-white',
                    // Active states - Light mode
                    isActive && !isDark && [
                      action.color === 'blue' && 'bg-blue-100 text-blue-700 border border-blue-200',
                      action.color === 'purple' && 'bg-purple-100 text-purple-700 border border-purple-200',
                      action.color === 'green' && 'bg-green-100 text-green-700 border border-green-200',
                    ],
                    // Active states - Dark mode with glow
                    isActive && isDark && [
                      action.color === 'blue' && 'bg-neon-blue/15 text-neon-blue border border-neon-blue/40 shadow-[0_0_20px_rgba(0,245,255,0.2)]',
                      action.color === 'purple' && 'bg-neon-purple/15 text-neon-purple border border-neon-purple/40 shadow-[0_0_20px_rgba(191,0,255,0.2)]',
                      action.color === 'green' && 'bg-neon-green/15 text-neon-green border border-neon-green/40 shadow-[0_0_20px_rgba(0,255,136,0.2)]',
                    ],
                  )}
                >
                  {({ isActive: isActiveItem }) => (
                    <>
                      {/* Background effect for dark mode */}
                      {isDark && (
                        <div className={clsx(
                          'absolute inset-0 opacity-0 transition-opacity duration-300',
                          action.color === 'blue' && 'bg-gradient-to-r from-neon-blue/10 to-transparent',
                          action.color === 'purple' && 'bg-gradient-to-r from-neon-purple/10 to-transparent',
                          action.color === 'green' && 'bg-gradient-to-r from-neon-green/10 to-transparent',
                        )} />
                      )}

                      {/* Icon Container */}
                      <div className={clsx(
                        'relative z-10 p-2 rounded-lg flex-shrink-0 transition-all duration-200',
                        // Light mode
                        !isDark && action.color === 'blue' && 'bg-blue-500/10',
                        !isDark && action.color === 'purple' && 'bg-purple-500/10',
                        !isDark && action.color === 'green' && 'bg-green-500/10',
                        // Dark mode with glow
                        isDark && action.color === 'blue' && 'bg-neon-blue/20 group-hover:bg-neon-blue/30 shadow-[0_0_10px_rgba(0,245,255,0.3)]',
                        isDark && action.color === 'purple' && 'bg-neon-purple/20 group-hover:bg-neon-purple/30 shadow-[0_0_10px_rgba(191,0,255,0.3)]',
                        isDark && action.color === 'green' && 'bg-neon-green/20 group-hover:bg-neon-green/30 shadow-[0_0_10px_rgba(0,255,136,0.3)]',
                      )}>
                        <action.icon
                          size={18}
                          className={clsx(
                            'transition-all duration-200',
                            // Light mode
                            !isDark && action.color === 'blue' && 'text-blue-600',
                            !isDark && action.color === 'purple' && 'text-purple-600',
                            !isDark && action.color === 'green' && 'text-green-600',
                            // Dark mode with glow
                            isDark && action.color === 'blue' && 'text-neon-blue drop-shadow-[0_0_8px_rgba(0,245,255,0.8)]',
                            isDark && action.color === 'purple' && 'text-neon-purple drop-shadow-[0_0_8px_rgba(191,0,255,0.8)]',
                            isDark && action.color === 'green' && 'text-neon-green drop-shadow-[0_0_8px_rgba(0,255,136,0.8)]',
                          )}
                        />
                      </div>

                      {/* Text Content */}
                      <div className="relative z-10 flex flex-col min-w-0 flex-1">
                        <span className={clsx(
                          'text-sm font-medium truncate transition-all',
                          // Light mode
                          !isDark && 'text-gray-900',
                          // Dark mode
                          isDark && [
                            action.color === 'blue' && 'text-neon-blue group-hover:text-white',
                            action.color === 'purple' && 'text-neon-purple group-hover:text-white',
                            action.color === 'green' && 'text-neon-green group-hover:text-white',
                          ],
                          isActiveItem && isDark && 'font-cyber',
                        )}>{action.name}</span>
                        <span className={clsx(
                          'text-xs truncate transition-colors',
                          !isDark && 'text-gray-500',
                          isDark && 'text-gray-500 group-hover:text-gray-400',
                        )}>{action.desc}</span>
                      </div>

                      {/* Arrow indicator */}
                      <div className={clsx(
                        'relative z-10 opacity-0 -translate-x-2 transition-all duration-200',
                        'group-hover:opacity-100 group-hover:translate-x-0',
                        isDark ? 'text-gray-400' : 'text-gray-400'
                      )}>
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </div>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* ========================================
          BOTTOM SECTION - Settings
          ======================================== */}
      <div className={clsx(
        'shrink-0 p-3 border-t',
        isDark ? 'border-neon-blue/20 bg-cyber-card/50' : 'border-gray-200 bg-gray-50'
      )}>
        <NavLink
          to="/app/settings"
          onMouseEnter={() => setHoveredItem('settings')}
          onMouseLeave={() => setHoveredItem(null)}
          className={({ isActive }) => clsx(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200',
            'group relative',
            // Base
            !isActive && !isDark && 'text-gray-600 hover:bg-gray-100 hover:text-gray-900',
            !isActive && isDark && 'text-gray-300 hover:text-neon-blue',
            // Light mode active
            isActive && !isDark && 'bg-gray-100 text-gray-900 font-medium',
            // Dark mode active
            isActive && isDark && [
              'bg-gradient-to-r from-neon-blue/20 to-cyan-500/20',
              'text-neon-blue font-cyber',
              'border border-neon-blue/40',
              'shadow-[0_0_15px_rgba(0,245,255,0.3)]',
            ],
            !sidebarOpen && 'justify-center',
          )}
        >
          {({ isActive }) => (
            <>
              <Settings
                size={20}
                className={clsx(
                  'shrink-0 transition-all duration-200',
                  isActive
                    ? isDark ? 'text-neon-blue drop-shadow-[0_0_8px_rgba(0,245,255,0.8)]' : 'text-gray-700'
                    : isDark ? 'text-gray-400 group-hover:text-neon-blue' : 'text-gray-500 group-hover:text-gray-700'
                )}
              />
              {sidebarOpen && (
                <span className={clsx(
                  'truncate transition-all',
                  isActive && 'font-medium',
                  isDark && 'tracking-wide group-hover:text-neon-blue'
                )}>{t('nav.settings')}</span>
              )}
              {/* Hover tooltip when collapsed */}
              {!sidebarOpen && hoveredItem === 'settings' && (
                <div className={clsx(
                  'absolute left-full ml-2 px-3 py-1.5 rounded-lg text-sm whitespace-nowrap z-50',
                  'animate-fade-in',
                  isDark
                    ? 'bg-cyber-card border border-neon-blue/40 text-neon-blue shadow-[0_0_15px_rgba(0,245,255,0.2)]'
                    : 'bg-white text-gray-900 shadow-lg border border-gray-200'
                )}>
                  {t('nav.settings')}
                </div>
              )}
            </>
          )}
        </NavLink>

        {/* Back to home link */}
        {sidebarOpen && (
          <Link
            to="/"
            className={clsx(
              'flex items-center gap-3 px-3 py-2 mt-2 rounded-lg transition-all duration-200',
              'group',
              isDark
                ? 'text-gray-500 hover:text-neon-green hover:bg-neon-green/5'
                : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
            )}
          >
            <Home size={18} className="shrink-0" />
            <span className={clsx(
              'text-sm',
              isDark && 'font-cyber'
            )}>
              Back to Home
            </span>
          </Link>
        )}
      </div>
    </aside>
  )
}
