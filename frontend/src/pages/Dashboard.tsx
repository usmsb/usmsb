import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import {
  Users,
  FlaskConical,
  Activity,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Cpu,
  Database,
  PlusCircle,
  Target,
} from 'lucide-react'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Line,
  BarChart,
  Bar,
} from 'recharts'
import { getMetrics, getAgents, getWorkflows, getStatsSummary, getSystemStatus, authFetch } from '@/lib/api'
import { WelcomeGuide } from '@/components/WelcomeGuide'
import { ListItemSkeleton } from '@/components/ui/EmptyState'
import { WalletBalanceCard, TransactionList } from '@/components/WalletBalance'
import { ReputationDisplay } from '@/components/ReputationDisplay'
import { BlockchainStatusCard, TokenBalanceChecker } from '@/components/BlockchainStatus'
import { useAppStore } from '@/store'
import clsx from 'clsx'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function Dashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
  })

  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['agents'],
    queryFn: () => getAgents(undefined, 5),
  })

  const { data: _workflows } = useQuery({
    queryKey: ['workflows'],
    queryFn: getWorkflows,
  })

  const { data: statsSummary } = useQuery({
    queryKey: ['stats-summary'],
    queryFn: getStatsSummary,
  })

  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: getSystemStatus,
  })

  const { data: environmentState } = useQuery({
    queryKey: ['environment'],
    queryFn: async () => {
      const response = await authFetch(`${API_BASE}/environment/state`)
      if (!response.ok) throw new Error('Failed to fetch environment state')
      return response.json()
    },
  })

  // Calculate active agents from environment state
  const activeAgentsCount = environmentState?.active_agents || metrics?.agents_count || 0
  const totalAgentsCount = environmentState?.total_agents || metrics?.agents_count || 0
  const activeDemands = environmentState?.active_demands || 0
  const activeServices = environmentState?.active_services || 0

  // Build activity data from real metrics (use current data as baseline)
  const activityData = metrics?.daily_activity || [
    { name: 'Today', agents: totalAgentsCount, predictions: activeDemands, workflows: activeServices },
  ]

  // Build token usage from real metrics
  const tokenUsageData = metrics?.weekly_usage || [
    { name: 'Current', used: metrics?.intelligence_sources?.total_tokens || 0 },
  ]

  // Neon color mapping for dynamic styles
  const neonColorMap: Record<string, { color: string; textClass: string; bgClass: string }> = {
    'neon-blue': { color: '#00f5ff', textClass: 'text-neon-blue', bgClass: 'bg-neon-blue' },
    'neon-purple': { color: '#bf00ff', textClass: 'text-neon-purple', bgClass: 'bg-neon-purple' },
    'neon-green': { color: '#00ff88', textClass: 'text-neon-green', bgClass: 'bg-neon-green' },
    'neon-pink': { color: '#ff00ff', textClass: 'text-neon-pink', bgClass: 'bg-neon-pink' },
  }

  const stats = [
    {
      name: t('dashboard.totalAgents'),
      value: statsSummary?.total_agents || totalAgentsCount,
      icon: Users,
      change: `${statsSummary?.online_agents || 0} online`,
      changeType: 'increase' as const,
      neonColor: 'neon-blue',
    },
    {
      name: t('dashboard.activeAgents'),
      value: statsSummary?.online_agents || activeAgentsCount,
      icon: FlaskConical,
      change: `${statsSummary?.bound_agents || 0} bound`,
      changeType: 'increase' as const,
      neonColor: 'neon-purple',
    },
    {
      name: t('dashboard.pendingTasks'),
      value: statsSummary?.active_demands || activeDemands,
      icon: Activity,
      change: 'Open demands',
      changeType: 'increase' as const,
      neonColor: 'neon-green',
    },
    {
      name: t('dashboard.completedTasks'),
      value: statsSummary?.active_collaborations || activeServices,
      icon: DollarSign,
      change: `${statsSummary?.total_stake?.toLocaleString() || 0} VIBE staked`,
      changeType: 'increase' as const,
      neonColor: 'neon-pink',
    },
  ]

  // Cyberpunk chart colors
  const chartColors = isDark ? {
    primary: '#00f5ff',
    secondary: '#bf00ff',
    tertiary: '#00ff88',
    grid: 'rgba(0, 245, 255, 0.1)',
    text: '#94a3b8',
  } : {
    primary: '#0ea5e9',
    secondary: '#22c55e',
    tertiary: '#8b5cf6',
    grid: '#e2e8f0',
    text: '#475569',
  }

  return (
    <div className="space-y-6">
      {/* Welcome Guide for first-time users */}
      <WelcomeGuide />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className={clsx(
            'text-xl md:text-2xl font-bold',
            'text-light-text-primary',
            isDark && 'text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber'
          )}>{t('dashboard.title')}</h1>
          <p className={clsx(
            'text-light-text-muted',
            isDark && 'text-gray-400'
          )}>{t('dashboard.welcome')}</p>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <button
            onClick={() => navigate('/publish/service')}
            className="btn btn-primary flex items-center gap-2"
          >
            <PlusCircle size={18} />
            {t('dashboard.publishService')}
          </button>
          <button
            onClick={() => navigate('/publish/demand')}
            className="btn btn-secondary flex items-center gap-2"
          >
            <Target size={18} />
            {t('dashboard.publishDemand')}
          </button>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <div
            key={stat.name}
            className={clsx(
              'card group relative overflow-hidden',
              isDark && 'hover:border-neon-blue/50'
            )}
            style={isDark ? { animationDelay: `${index * 100}ms` } : undefined}
          >
            {/* Holographic effect overlay */}
            {isDark && (
              <div className="absolute inset-0 bg-gradient-to-br from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            )}
            <div className="relative z-10">
              <div className="flex items-center justify-between">
                <div>
                  <p className={clsx(
                    'text-sm',
                    'text-light-text-muted',
                    isDark && 'text-neon-blue/70 font-cyber tracking-wider'
                  )}>{stat.name}</p>
                  <p
                    className={clsx(
                      'text-2xl font-bold mt-1',
                      'text-light-text-primary',
                      isDark && 'font-cyber'
                    )}
                    style={isDark ? {
                      color: neonColorMap[stat.neonColor]?.color,
                      textShadow: `0 0 10px ${neonColorMap[stat.neonColor]?.color}`,
                    } : undefined}
                  >
                    {stat.value.toLocaleString()}
                  </p>
                </div>
                <div className={clsx(
                  'w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300',
                  'bg-gradient-to-br from-blue-100 to-purple-100',
                  isDark && 'bg-transparent border border-neon-blue/30 group-hover:shadow-[0_0_15px_var(--neon-blue)]'
                )}>
                  <stat.icon
                    className={clsx(
                      'transition-all duration-300',
                      'text-primary-600',
                      isDark && 'text-neon-blue group-hover:drop-shadow-[0_0_8px_var(--neon-blue)]'
                    )}
                    size={24}
                  />
                </div>
              </div>
              <div className="mt-4 flex items-center gap-1">
                {stat.changeType === 'increase' ? (
                  <TrendingUp className={clsx(
                    'text-green-500',
                    isDark && 'text-neon-green'
                  )} size={16} />
                ) : (
                  <TrendingDown className={clsx(
                    'text-red-500',
                    isDark && 'text-neon-pink'
                  )} size={16} />
                )}
                <span
                  className={clsx(
                    'text-sm font-medium',
                    stat.changeType === 'increase' ? 'text-green-500' : 'text-red-500',
                    isDark && (stat.changeType === 'increase' ? 'text-neon-green' : 'text-neon-pink')
                  )}
                >
                  {stat.change}
                </span>
                <span className={clsx(
                  'text-sm',
                  'text-light-text-muted',
                  isDark && 'text-gray-500'
                )}>{t('dashboard.recentActivity')}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Activity chart */}
        <div className={clsx(
          'card',
          isDark && 'hologram'
        )}>
          <h3 className={clsx(
            'text-base md:text-lg font-semibold mb-4',
            'text-light-text-primary',
            isDark && 'text-neon-blue font-cyber'
          )}>{t('dashboard.recentActivity')}</h3>
          <div className="h-56 md:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="colorAgents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartColors.primary} stopOpacity={isDark ? 0.4 : 0.3} />
                    <stop offset="95%" stopColor={chartColors.primary} stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPredictions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={chartColors.tertiary} stopOpacity={0.4} />
                    <stop offset="95%" stopColor={chartColors.tertiary} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                <XAxis dataKey="name" stroke={chartColors.text} />
                <YAxis stroke={chartColors.text} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#0d0d14' : '#fff',
                    border: isDark ? '1px solid rgba(0, 245, 255, 0.3)' : '1px solid #e2e8f0',
                    borderRadius: '8px',
                    color: isDark ? '#00f5ff' : '#1f2937',
                    boxShadow: isDark ? '0 0 20px rgba(0, 245, 255, 0.2)' : 'none',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="agents"
                  stroke={chartColors.primary}
                  fillOpacity={1}
                  fill="url(#colorAgents)"
                />
                <Line type="monotone" dataKey="predictions" stroke={chartColors.tertiary} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Token usage chart */}
        <div className={clsx(
          'card',
          isDark && 'hologram'
        )}>
          <h3 className={clsx(
            'text-base md:text-lg font-semibold mb-4',
            'text-light-text-primary',
            isDark && 'text-neon-purple font-cyber'
          )}>{t('dashboard.completedTasks')}</h3>
          <div className="h-56 md:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={tokenUsageData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                <XAxis dataKey="name" stroke={chartColors.text} />
                <YAxis stroke={chartColors.text} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: isDark ? '#0d0d14' : '#fff',
                    border: isDark ? '1px solid rgba(191, 0, 255, 0.3)' : '1px solid #e2e8f0',
                    borderRadius: '8px',
                    color: isDark ? '#bf00ff' : '#1f2937',
                    boxShadow: isDark ? '0 0 20px rgba(191, 0, 255, 0.2)' : 'none',
                  }}
                />
                <Bar
                  dataKey="used"
                  fill={isDark ? '#bf00ff' : '#0ea5e9'}
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent agents */}
        <div className="card lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className={clsx(
              'text-lg font-semibold',
              'text-light-text-primary',
              isDark && 'text-neon-blue font-cyber'
            )}>{t('dashboard.recentActivity')}</h3>
            <a
              href="/app/agents"
              className={clsx(
                'text-sm transition-colors',
                'text-primary-600 hover:text-primary-700',
                isDark && 'text-neon-blue hover:text-white'
              )}
            >
              {t('common.search')}
            </a>
          </div>
          {agentsLoading ? (
            <div className="space-y-4">
              <ListItemSkeleton />
              <ListItemSkeleton />
              <ListItemSkeleton />
            </div>
          ) : agents && agents.length > 0 ? (
            <div className="space-y-4">
              {agents?.map((agent, index) => (
                <div
                  key={agent.id ?? `agent-${index}`}
                  className={clsx(
                    'flex items-center justify-between p-4 rounded-lg transition-all duration-300',
                    'bg-secondary-50',
                    isDark && 'bg-cyber-dark/50 border border-neon-blue/10 hover:border-neon-blue/30 hover:shadow-[0_0_15px_rgba(0,245,255,0.1)]'
                  )}
                  style={isDark ? { animationDelay: `${index * 100}ms` } : undefined}
                >
                  <div className="flex items-center gap-4">
                    <div className={clsx(
                      'w-10 h-10 rounded-full flex items-center justify-center',
                      'bg-primary-100',
                      isDark && 'bg-neon-blue/10 border border-neon-blue/30'
                    )}>
                      <Users className={clsx(
                        'text-primary-600',
                        isDark && 'text-neon-blue'
                      )} size={20} />
                    </div>
                    <div>
                      <p className={clsx(
                        'font-medium',
                        'text-light-text-primary',
                        isDark && 'text-gray-100'
                      )}>{agent.name}</p>
                      <p className={clsx(
                        'text-sm',
                        'text-light-text-muted',
                        isDark && 'text-gray-500 font-mono'
                      )}>{agent.type}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={clsx(
                      'text-sm font-medium',
                      'text-light-text-primary',
                      isDark && 'text-neon-green'
                    )}>
                      {agent.capabilities.length} capabilities
                    </p>
                    <p className={clsx(
                      'text-sm',
                      'text-light-text-muted',
                      isDark && 'text-gray-500'
                    )}>
                      {agent.goals_count} goals
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center">
              <Users className={clsx(
                'w-12 h-12 mx-auto mb-3',
                'text-secondary-300',
                isDark && 'text-neon-blue/30'
              )} />
              <p className={clsx(
                'text-light-text-muted',
                isDark && 'text-gray-400'
              )}>{t('empty.noAgents')}</p>
              <button
                onClick={() => navigate('/app/agents')}
                className={clsx(
                  'mt-3 text-sm hover:underline',
                  'text-primary-600',
                  isDark && 'text-neon-blue'
                )}
              >
                {t('empty.addFirst')}
              </button>
            </div>
          )}
        </div>

        {/* System resources */}
        <div className="card">
          <h3 className={clsx(
            'text-lg font-semibold mb-4',
            'text-light-text-primary',
            isDark && 'text-neon-purple font-cyber'
          )}>{t('nav.simulations')}</h3>
          <div className="space-y-4">
            {[
              { icon: Cpu, label: 'CPU', value: '45%', colorKey: 'neon-green', width: '45%', lightClass: 'bg-green-500' },
              { icon: Database, label: 'RAM', value: '62%', colorKey: 'neon-blue', width: '62%', lightClass: 'bg-blue-500' },
              { icon: Activity, label: 'API', value: '128ms', colorKey: 'neon-purple', width: '25%', lightClass: 'bg-purple-500' },
            ].map((item) => {
              const neonColor = neonColorMap[item.colorKey]
              return (
                <div key={item.label} className="flex items-center gap-4">
                  <div
                    className="w-10 h-10 rounded-lg flex items-center justify-center transition-all"
                    style={isDark ? {
                      backgroundColor: `color-mix(in srgb, ${neonColor.color} 10%, transparent)`,
                      border: `1px solid color-mix(in srgb, ${neonColor.color} 30%, transparent)`,
                    } : undefined}
                  >
                    <item.icon
                      className={clsx(!isDark && 'text-secondary-600')}
                      style={isDark ? { color: neonColor.color } : undefined}
                      size={20}
                    />
                  </div>
                  <div className="flex-1">
                    <div className="flex justify-between mb-1">
                      <span className={clsx(
                        'text-sm',
                        'text-secondary-600',
                        isDark && 'text-gray-400 font-mono'
                      )}>{item.label}</span>
                      <span
                        className={clsx(
                          'text-sm font-medium',
                          'text-light-text-primary',
                          isDark && 'font-cyber'
                        )}
                        style={isDark ? { color: neonColor.color } : undefined}
                      >{item.value}</span>
                    </div>
                    <div className={clsx(
                      'w-full rounded-full h-2 overflow-hidden',
                      'bg-secondary-200',
                      isDark && 'bg-cyber-dark border border-neon-blue/20'
                    )}>
                      <div
                        className={clsx(
                          'h-2 rounded-full transition-all duration-500',
                          !isDark && item.lightClass
                        )}
                        style={isDark ? {
                          backgroundColor: neonColor.color,
                          width: item.width,
                          boxShadow: `0 0 10px ${neonColor.color}`,
                        } : { width: item.width }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>

      {/* Wallet & Reputation Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <WalletBalanceCard />
        <ReputationDisplay showHistory={true} />
        <BlockchainStatusCard />
      </div>

      {/* Transactions & Blockchain Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className={clsx(
            'text-lg font-semibold mb-4',
            'text-light-text-primary',
            isDark && 'text-neon-blue font-cyber'
          )}>{t('dashboard.recentTransactions', 'Recent Transactions')}</h3>
          <TransactionList limit={5} />
        </div>
        <TokenBalanceChecker />
      </div>

      {/* System Status */}
      {systemStatus && (
        <div className="card">
          <h3 className={clsx(
            'text-lg font-semibold mb-4',
            'text-light-text-primary',
            isDark && 'text-neon-green font-cyber'
          )}>{t('dashboard.systemStatus', 'System Status')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-gray-800/30 rounded-lg">
              <p className="text-sm text-gray-400">Version</p>
              <p className="text-lg font-bold text-white">{systemStatus.version}</p>
            </div>
            <div className="p-4 bg-gray-800/30 rounded-lg">
              <p className="text-sm text-gray-400">Uptime</p>
              <p className="text-lg font-bold text-white">{systemStatus.uptime.days}d {Math.floor(systemStatus.uptime.hours % 24)}h</p>
            </div>
            <div className="p-4 bg-gray-800/30 rounded-lg">
              <p className="text-sm text-gray-400">Services</p>
              <div className="flex items-center gap-2">
                <span className={clsx(
                  'w-2 h-2 rounded-full',
                  systemStatus.services.llm ? 'bg-green-400' : 'bg-red-400'
                )} />
                <span className={clsx(
                  'w-2 h-2 rounded-full',
                  systemStatus.services.meta_agent ? 'bg-green-400' : 'bg-red-400'
                )} />
                <span className={clsx(
                  'w-2 h-2 rounded-full',
                  systemStatus.services.prediction ? 'bg-green-400' : 'bg-red-400'
                )} />
                <span className={clsx(
                  'w-2 h-2 rounded-full',
                  systemStatus.services.workflow ? 'bg-green-400' : 'bg-red-400'
                )} />
              </div>
            </div>
            <div className="p-4 bg-gray-800/30 rounded-lg">
              <p className="text-sm text-gray-400">Platform</p>
              <p className="text-lg font-bold text-white">{systemStatus.platform.system}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
