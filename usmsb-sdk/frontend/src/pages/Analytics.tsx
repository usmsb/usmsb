import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts'
import { TrendingUp, Users, Activity, Zap, BarChart3 } from 'lucide-react'
import { getMetrics } from '@/lib/api'
import { useAppStore } from '@/store'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

export default function Analytics() {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const { data: metrics } = useQuery({
    queryKey: ['metrics'],
    queryFn: getMetrics,
  })

  const { data: environmentState } = useQuery({
    queryKey: ['environment'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/environment/state`)
      if (!response.ok) throw new Error('Failed to fetch environment state')
      return response.json()
    },
  })

  const { data: governanceStats } = useQuery({
    queryKey: ['governance-stats'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/governance/stats`)
      if (!response.ok) throw new Error('Failed to fetch governance stats')
      return response.json()
    },
  })

  // Build agent distribution from real data
  const agentDistributionData = [
    { name: 'AI Agents', value: environmentState?.ai_agents || 0, color: '#0ea5e9' },
    { name: 'Human', value: environmentState?.human_agents || 0, color: '#22c55e' },
    { name: 'External', value: environmentState?.external_agents || 0, color: '#8b5cf6' },
  ].filter(d => d.value > 0) // Only show categories with values

  // If no data, show placeholder
  const hasAgentData = agentDistributionData.length > 0

  // Build prediction accuracy data from metrics (placeholder if no historical data)
  const metricsData = metrics as Record<string, unknown> | undefined
  const intelligenceSources = metricsData?.intelligence_sources as Record<string, unknown> | undefined
  const predictionAccuracyData = [
    { name: 'Current', accuracy: intelligenceSources?.success_rate
      ? (intelligenceSources.success_rate as number) * 100
      : 95 },
  ]

  // Build resource usage from environment state
  const resourceUsageData = [
    { name: 'Agents', used: environmentState?.active_agents || 0, available: (environmentState?.total_agents || 0) - (environmentState?.active_agents || 0) },
    { name: 'Demands', used: environmentState?.active_demands || 0, available: 0 },
    { name: 'Services', used: environmentState?.active_services || 0, available: 0 },
    { name: 'Transactions', used: environmentState?.total_transactions || 0, available: 0 },
  ]

  // Calculate real stats from API data
  const totalPredictions = governanceStats?.total_votes || intelligenceSources?.total_requests || 0
  const activeAgents = environmentState?.active_agents || metricsData?.agents_count || 0
  const avgResponseTime = '---'  // Would need real monitoring data
  const successRate = intelligenceSources?.success_rate
    ? `${((intelligenceSources.success_rate as number) * 100).toFixed(1)}%`
    : '---'

  const stats = [
    {
      name: t('analytics.totalPredictions'),
      value: totalPredictions.toLocaleString(),
      change: 'Total',
      icon: TrendingUp,
      color: 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    },
    {
      name: t('analytics.activeAgents'),
      value: activeAgents,
      change: 'Active',
      icon: Users,
      color: 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
    },
    {
      name: t('analytics.avgResponseTime'),
      value: avgResponseTime,
      change: 'Avg',
      icon: Activity,
      color: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
    },
    {
      name: t('analytics.successRate'),
      value: successRate,
      change: 'Success',
      icon: Zap,
      color: 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
    },
  ]

  // Theme-aware chart colors
  const chartColors = {
    grid: isDark ? '#374151' : '#e2e8f0',
    axis: isDark ? '#9ca3af' : '#94a3b8',
    tooltip: {
      bg: isDark ? '#1f2937' : '#fff',
      border: isDark ? '#374151' : '#e2e8f0',
      text: isDark ? '#f3f4f6' : '#1f2937',
    },
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">{t('analytics.title')}</h1>
        <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">{t('analytics.predictionAccuracyTrend')}</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.name} className="card">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${stat.color}`}>
                <stat.icon size={20} />
              </div>
              <div>
                <p className="text-sm text-secondary-500 dark:text-secondary-400">{stat.name}</p>
                <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{stat.value}</p>
              </div>
            </div>
            <p className="mt-2 text-sm text-green-600 dark:text-green-400 font-medium">{stat.change} vs last month</p>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Prediction Accuracy */}
        <div className="card">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
            {t('analytics.predictionAccuracyTrend')}
          </h3>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={predictionAccuracyData}>
                <defs>
                  <linearGradient id="colorAccuracy" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
                <XAxis dataKey="name" stroke={chartColors.axis} />
                <YAxis stroke={chartColors.axis} domain={[70, 100]} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartColors.tooltip.bg,
                    border: `1px solid ${chartColors.tooltip.border}`,
                    borderRadius: '8px',
                    color: chartColors.tooltip.text,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="accuracy"
                  stroke="#22c55e"
                  fillOpacity={1}
                  fill="url(#colorAccuracy)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Agent Distribution */}
        <div className="card">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">{t('analytics.agentDistribution')}</h3>
          <div className="h-72 flex items-center justify-center">
            {hasAgentData ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={agentDistributionData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {agentDistributionData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: chartColors.tooltip.bg,
                      border: `1px solid ${chartColors.tooltip.border}`,
                      borderRadius: '8px',
                      color: chartColors.tooltip.text,
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-center text-secondary-500 dark:text-secondary-400">
                <BarChart3 size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
                <p>No agent data available</p>
                <p className="text-sm">Register agents to see distribution</p>
              </div>
            )}
          </div>
          {hasAgentData && (
            <div className="flex justify-center gap-6 mt-4">
              {agentDistributionData.map((item) => (
                <div key={item.name} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-secondary-600 dark:text-secondary-400">{item.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Resource Usage */}
      <div className="card">
        <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">{t('analytics.resourceUsage')}</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={resourceUsageData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke={chartColors.grid} />
              <XAxis type="number" stroke={chartColors.axis} />
              <YAxis dataKey="name" type="category" stroke={chartColors.axis} width={80} />
              <Tooltip
                contentStyle={{
                  backgroundColor: chartColors.tooltip.bg,
                  border: `1px solid ${chartColors.tooltip.border}`,
                  borderRadius: '8px',
                  color: chartColors.tooltip.text,
                }}
              />
              <Bar dataKey="used" fill="#0ea5e9" name="Used %" />
              <Bar dataKey="available" fill={isDark ? '#374151' : '#e2e8f0'} name="Available %" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Intelligence Source Metrics */}
      {metrics?.intelligence_sources && (
        <div className="card">
          <h3 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">
            {t('analytics.intelligenceSourceMetrics')}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-secondary-50 dark:bg-secondary-700/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                {metrics.intelligence_sources.total_sources}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('analytics.totalSources')}</p>
            </div>
            <div className="p-4 bg-secondary-50 dark:bg-secondary-700/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                {metrics.intelligence_sources.total_requests.toLocaleString()}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('analytics.totalRequests')}</p>
            </div>
            <div className="p-4 bg-secondary-50 dark:bg-secondary-700/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                {(metrics.intelligence_sources.success_rate * 100).toFixed(1)}%
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('analytics.successRateLabel')}</p>
            </div>
            <div className="p-4 bg-secondary-50 dark:bg-secondary-700/50 rounded-lg text-center">
              <p className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
                ${metrics.intelligence_sources.total_cost.toFixed(2)}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('analytics.totalCost')}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
