import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  Plus,
  Search,
  Filter,
  Bot,
  User,
  Settings,
  Link2,
  MessageSquare,
  FileCode,
  RefreshCw,
  Zap,
  Star,
  Clock,
  Wallet,
  AlertTriangle,
  Shield,
} from 'lucide-react'
import clsx from 'clsx'
import { EmptyState } from '@/components/ui'
import { getStatusColor } from '@/utils/statusColors'
import { authFetch } from '@/lib/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

interface AIAgent {
  agent_id: string
  name: string
  agent_type: string
  capabilities: string[]
  skills: Array<{ name: string; level?: string }>
  endpoint: string
  protocol: string
  stake: number
  description: string
  status: string
  reputation: number
  registered_at: number
  last_heartbeat: number
  has_wallet_binding: boolean
}

// Raw API response type (capabilities/skills may be string or array)
interface AIAgentApiResponse {
  agent_id: string
  name: string
  agent_type: string
  capabilities: string[] | string
  skills: Array<{ name: string; level?: string }> | string
  endpoint: string
  protocol: string
  stake: number
  description: string
  status: string
  reputation: number
  registered_at: number
  last_heartbeat: number
  has_wallet_binding?: boolean
}

type ProtocolFilter = 'all' | 'standard' | 'mcp' | 'a2a' | 'skill_md'
type AgentTypeFilter = 'all' | 'human_agent' | 'ai_agent' | 'system_agent'

export default function Agents() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState('')
  const [protocolFilter, setProtocolFilter] = useState<ProtocolFilter>('all')
  const [agentTypeFilter, setAgentTypeFilter] = useState<AgentTypeFilter>('all')

  // Fetch AI agents from database
  const { data: agents, isLoading, refetch } = useQuery({
    queryKey: ['ai-agents'],
    queryFn: async () => {
      const response = await authFetch(`${API_BASE}/agents`)
      if (!response.ok) throw new Error('Failed to fetch agents')
      const data = await response.json() as AIAgentApiResponse[]
      // Transform data to ensure arrays are properly parsed
      return data.map((agent) => ({
        ...agent,
        capabilities: Array.isArray(agent.capabilities)
          ? agent.capabilities
          : (typeof agent.capabilities === 'string'
              ? (agent.capabilities ? JSON.parse(agent.capabilities) : [])
              : []),
        skills: Array.isArray(agent.skills)
          ? agent.skills
          : (typeof agent.skills === 'string'
              ? (agent.skills ? JSON.parse(agent.skills) : [])
              : []),
      })) as AIAgent[]
    },
  })

  // Filter agents
  const filteredAgents = agents?.filter((agent) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesName = agent.name.toLowerCase().includes(query)
      const matchesCapabilities = agent.capabilities.some((c) => c.toLowerCase().includes(query))
      if (!matchesName && !matchesCapabilities) return false
    }

    // Protocol filter
    if (protocolFilter !== 'all' && agent.protocol !== protocolFilter) {
      return false
    }

    // Agent type filter
    if (agentTypeFilter !== 'all' && agent.agent_type !== agentTypeFilter) {
      return false
    }

    return true
  })

  const getProtocolInfo = (protocol: string | undefined) => {
    const proto = (protocol || 'standard').toLowerCase()
    switch (proto) {
      case 'mcp':
        return { icon: Link2, color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400', label: 'MCP' }
      case 'a2a':
        return { icon: MessageSquare, color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400', label: 'A2A' }
      case 'skill_md':
        return { icon: FileCode, color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400', label: 'Skills.md' }
      default:
        return { icon: Bot, color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', label: 'Standard' }
    }
  }

  // Get agent type info for display
  const getAgentTypeInfo = (agentType: string | undefined) => {
    const type = agentType || 'ai_agent'
    switch (type) {
      case 'human_agent':
        return { icon: User, color: 'bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400', label: t('agents.humanAgent', 'Human') }
      case 'system_agent':
        return { icon: Settings, color: 'bg-gray-100 text-gray-600 dark:bg-gray-900/30 dark:text-gray-400', label: t('agents.systemAgent', 'System') }
      default:
        return { icon: Bot, color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', label: t('agents.aiAgent', 'AI') }
    }
  }

  const formatTime = (timestamp: number) => {
    if (!timestamp) return 'N/A'
    const date = new Date(timestamp * 1000)
    const now = new Date()
    const diff = now.getTime() - date.getTime()

    if (diff < 60000) return t('agents.justNow')
    if (diff < 3600000) return `${Math.floor(diff / 60000)}${t('agents.minAgo')}`
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}${t('agents.hAgo')}`
    return date.toLocaleDateString()
  }

  // Calculate time remaining before auto-unregister (24 hours grace period)
  const getAutoUnregisterInfo = (agent: AIAgent) => {
    // If has wallet binding, will never be auto-unregistered
    if (agent.has_wallet_binding) {
      return { protected: true, remaining: null, warning: false }
    }

    // If online, no warning
    if (agent.status === 'online') {
      return { protected: false, remaining: null, warning: false }
    }

    // Calculate remaining time (24 hours = 86400 seconds grace period)
    const gracePeriod = 24 * 60 * 60 // 24 hours in seconds
    const lastHeartbeat = agent.last_heartbeat || 0
    const now = Math.floor(Date.now() / 1000)
    const elapsed = now - lastHeartbeat
    const remaining = gracePeriod - elapsed

    if (remaining <= 0) {
      return { protected: false, remaining: 0, warning: true, critical: true }
    }

    // Warning if less than 6 hours remaining
    const warning = remaining < 6 * 60 * 60

    return { protected: false, remaining, warning, critical: remaining < 1 * 60 * 60 }
  }

  const formatRemainingTime = (seconds: number) => {
    if (seconds <= 0) return t('agents.expiringSoon', 'Expiring soon')
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)

    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">{t('agents.aiAgents')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">{t('agents.manageAgents')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => navigate('/agents/register')}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus size={20} />
            <span className="hidden sm:inline">{t('agents.registerAIAgent')}</span>
            <span className="sm:hidden">{t('agents.registerAgent')}</span>
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 md:gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
              <Bot className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{agents?.filter((a) => a.agent_type === 'ai_agent').length || 0}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('agents.aiAgents', 'AI Agents')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 dark:bg-amber-900/30 rounded-lg flex items-center justify-center">
              <User className="text-amber-600 dark:text-amber-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{agents?.filter((a) => a.agent_type === 'human_agent').length || 0}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('agents.humanAgents', 'Human Agents')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
              <Zap className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {agents?.filter((a) => a.status === 'online').length || 0}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('agents.online')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
              <Link2 className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {agents?.filter((a) => a.protocol === 'mcp').length || 0}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('agents.mcpProtocol')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg flex items-center justify-center">
              <Star className="text-yellow-600 dark:text-yellow-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {agents && agents.length > 0
                  ? Math.round((agents.reduce((sum, a) => sum + (a.reputation || 0.5), 0) / agents.length) * 100)
                  : 0}%
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('agents.avgReputation')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="flex flex-col gap-4">
          <div className="relative w-full">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-400 dark:text-secondary-500"
              size={20}
            />
            <input
              type="text"
              placeholder={t('agents.searchAgentsByCapability')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 w-full dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
            />
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Filter size={20} className="text-secondary-400 dark:text-secondary-500 flex-shrink-0" />
            {/* Agent Type Filter */}
            <select
              value={agentTypeFilter}
              onChange={(e) => setAgentTypeFilter(e.target.value as AgentTypeFilter)}
              className="input flex-1 md:w-36 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
            >
              <option value="all">{t('agents.allTypes', 'All Types')}</option>
              <option value="ai_agent">{t('agents.aiAgents', 'AI Agents')}</option>
              <option value="human_agent">{t('agents.humanAgents', 'Human Agents')}</option>
              <option value="system_agent">{t('agents.systemAgents', 'System Agents')}</option>
            </select>
            {/* Protocol Filter */}
            <select
              value={protocolFilter}
              onChange={(e) => setProtocolFilter(e.target.value as ProtocolFilter)}
              className="input flex-1 md:w-40 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
            >
              <option value="all">{t('agents.allProtocols')}</option>
              <option value="standard">{t('agents.standard')}</option>
              <option value="mcp">{t('agents.mcp')}</option>
              <option value="a2a">{t('agents.a2a')}</option>
              <option value="skill_md">{t('agents.skillsMd')}</option>
            </select>
          </div>
        </div>
      </div>

      {/* Protocol Quick Register */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
        {[
          { protocol: 'standard', icon: Bot, color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', label: t('agents.standard') },
          { protocol: 'mcp', icon: Link2, color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400', label: t('agents.mcp') },
          { protocol: 'a2a', icon: MessageSquare, color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400', label: t('agents.a2a') },
          { protocol: 'skill_md', icon: FileCode, color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400', label: t('agents.skillsMd') },
        ].map((p) => (
          <button
            key={p.protocol}
            onClick={() => navigate(`/agents/register?protocol=${p.protocol}`)}
            className="card hover:shadow-md transition-shadow text-left dark:hover:bg-secondary-700/80"
          >
            <div className="flex items-center gap-3">
              <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', p.color)}>
                <p.icon size={20} />
              </div>
              <div>
                <p className="font-medium text-light-text-primary dark:text-secondary-100">{p.label}</p>
                <p className="text-xs text-secondary-500 dark:text-secondary-400">{t('agents.registerNewAgent')}</p>
              </div>
            </div>
          </button>
        ))}
      </div>

      {/* Agents Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={32} />
        </div>
      ) : filteredAgents && filteredAgents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredAgents.map((agent) => {
            const protocolInfo = getProtocolInfo(agent.protocol)
            const ProtocolIcon = protocolInfo.icon
            const typeInfo = getAgentTypeInfo(agent.agent_type)
            const TypeIcon = typeInfo.icon

            return (
              <div
                key={agent.agent_id}
                className="card hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => {
                  const agentId = agent.agent_id
                  if (agentId) {
                    navigate('/app/agents/' + agentId)
                  }
                }}
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={clsx('w-12 h-12 rounded-xl flex items-center justify-center', typeInfo.color)}>
                      <TypeIcon size={24} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{agent.name}</h3>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={clsx('px-2 py-0.5 rounded-full text-xs', typeInfo.color)}>{typeInfo.label}</span>
                        {/* Wallet binding indicator */}
                        {agent.has_wallet_binding && (
                          <span className="flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400">
                            <Wallet size={10} />
                            <span>{t('agents.walletBound', 'Wallet')}</span>
                          </span>
                        )}
                        <span className="text-xs text-secondary-500 dark:text-secondary-400">{protocolInfo.label}</span>
                        <span className={clsx('px-2 py-0.5 rounded-full text-xs', getStatusColor(agent.status))}>
                          {agent.status}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <Star className="text-yellow-500 dark:text-yellow-400" size={14} />
                    <span className="text-sm font-medium text-light-text-primary dark:text-secondary-100">{(agent.reputation * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="mb-4">
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 3).map((cap) => (
                      <span
                        key={cap}
                        className="px-2 py-0.5 bg-secondary-100 dark:bg-secondary-700 text-secondary-700 dark:text-secondary-300 text-xs rounded-full"
                      >
                        {cap}
                      </span>
                    ))}
                    {agent.capabilities.length > 3 && (
                      <span className="px-2 py-0.5 bg-secondary-100 dark:bg-secondary-700 text-secondary-700 dark:text-secondary-300 text-xs rounded-full">
                        +{agent.capabilities.length - 3}
                      </span>
                    )}
                  </div>
                </div>

                {/* Wallet Binding Status */}
                {agent.agent_type === 'ai_agent' && !agent.has_wallet_binding && agent.status === 'offline' && (
                  <div className="mb-2 px-2 py-1 bg-yellow-100 dark:bg-yellow-900/20 border border-yellow-300 dark:border-yellow-700 rounded text-xs text-yellow-700 dark:text-yellow-300 flex items-center gap-1">
                    <AlertTriangle size={12} />
                    <span>{t('agents.autoUnregisterWarning', 'No wallet - auto-unregister after 24h offline')}</span>
                  </div>
                )}

                {/* Stats */}
                <div className="flex items-center justify-between pt-4 border-t border-secondary-200 dark:border-secondary-700">
                  <div className="flex items-center gap-4 text-sm text-secondary-500 dark:text-secondary-400">
                    <div className="flex items-center gap-1">
                      <Zap size={14} />
                      <span>{agent.capabilities.length}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock size={14} />
                      <span>{formatTime(agent.last_heartbeat)}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {agent.has_wallet_binding ? (
                      <div className="flex items-center gap-1 text-green-500 dark:text-green-400">
                        <Shield size={14} />
                        <span className="text-xs">{t('agents.protected', 'Protected')}</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-gray-400 dark:text-gray-500">
                        <Wallet size={14} />
                        <span className="text-xs">{t('agents.noWallet', 'No wallet')}</span>
                      </div>
                    )}
                    <div className="text-sm font-medium text-light-text-primary dark:text-secondary-100">
                      {agent.stake} VIBE
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <EmptyState
          icon={Bot}
          title={t('agents.noAgentsRegistered')}
          description={t('agents.registerFirstAgent')}
          illustration="create"
          action={{
            label: t('agents.registerAgent'),
            onClick: () => navigate('/agents/register'),
            icon: Plus,
          }}
        />
      )}
    </div>
  )
}
