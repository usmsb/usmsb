import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Network,
  Search,
  Users,
  Globe,
  TrendingUp,
  Star,
  RefreshCw,
  UserPlus,
  MessageSquare,
  AlertCircle,
  Target,
  Info,
  Lightbulb,
  ChevronDown,
  ChevronUp,
  Shield,
} from 'lucide-react'
import { getStatusColor } from '@/utils/statusColors'
import { authFetch } from '@/lib/api'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

interface NetworkAgent {
  agent_id: string
  agent_name: string
  capabilities: string[]
  skills: string[]
  reputation: number
  status: string
}

interface AgentRecommendation {
  recommended_agent_id: string
  recommended_agent_name: string
  capability_match: number
  trust_score: number
  reason: string
}

interface NetworkStats {
  total_explorations: number
  total_discovered: number
  network_size: number
  trusted_agents: number
}

type ViewMode = 'explore' | 'network' | 'trusted' | 'recommendations'

export default function NetworkExplorer() {
  const { t } = useTranslation()

  // Use case examples with translations
  const useCaseExamples = [
    {
      title: t('network.useCase1Title'),
      description: t('network.useCase1Desc'),
      scenario: t('network.useCase1Scenario'),
      outcome: t('network.useCase1Outcome'),
    },
    {
      title: t('network.useCase2Title'),
      description: t('network.useCase2Desc'),
      scenario: t('network.useCase2Scenario'),
      outcome: t('network.useCase2Outcome'),
    },
    {
      title: t('network.useCase3Title'),
      description: t('network.useCase3Desc'),
      scenario: t('network.useCase3Scenario'),
      outcome: t('network.useCase3Outcome'),
    },
  ]

  const [viewMode, setViewMode] = useState<ViewMode>('explore')
  const [discoveredAgents, setDiscoveredAgents] = useState<NetworkAgent[]>([])
  const [recommendations, setRecommendations] = useState<AgentRecommendation[]>([])
  const [stats, setStats] = useState<NetworkStats>({
    total_explorations: 0,
    total_discovered: 0,
    network_size: 0,
    trusted_agents: 0,
  })
  const [isExploring, setIsExploring] = useState(false)
  const [targetCapability, setTargetCapability] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showInfo, setShowInfo] = useState(false)

  // Get current agent ID from localStorage
  const currentAgentId = localStorage.getItem('agent_id') || 'anonymous'

  // Fetch initial data on mount
  useEffect(() => {
    fetchStats()
    fetchAgents()
  }, [])

  const fetchStats = async () => {
    try {
      const response = await authFetch(`${API_BASE}/network/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch network stats:', err)
    }
  }

  const fetchAgents = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await authFetch(`${API_BASE}/agents`)
      if (response.ok) {
        const data = await response.json()
        const agents: NetworkAgent[] = data.map((a: Record<string, unknown>) => ({
          agent_id: a.agent_id as string || '',
          agent_name: a.name as string || 'Unknown',
          capabilities: Array.isArray(a.capabilities) ? a.capabilities : (typeof a.capabilities === 'string' ? JSON.parse(a.capabilities) : []),
          skills: Array.isArray(a.skills) ? a.skills : (typeof a.skills === 'string' ? JSON.parse(a.skills) : []),
          reputation: (a.reputation as number) || 0.5,
          status: (a.status as string) || 'offline',
        }))
        setDiscoveredAgents(agents)
      } else {
        setError('Failed to fetch agents')
      }
    } catch (err) {
      console.error('Failed to fetch agents:', err)
      setError('Network error. Please check if the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchRecommendations = async (capability: string) => {
    try {
      const response = await authFetch(`${API_BASE}/network/recommendations`, {
        method: 'POST',
        body: JSON.stringify({
          agent_id: currentAgentId,
          target_capability: capability,
        }),
      })
      if (response.ok) {
        const data = await response.json()
        setRecommendations(data)
      }
    } catch (err) {
      console.error('Failed to fetch recommendations:', err)
    }
  }

  const handleExplore = async () => {
    setIsExploring(true)
    setError(null)
    try {
      const response = await authFetch(`${API_BASE}/network/explore`, {
        method: 'POST',
        body: JSON.stringify({
          agent_id: currentAgentId,
          target_capabilities: targetCapability ? [targetCapability] : null,
          exploration_depth: 2,
        }),
      })
      if (response.ok) {
        const data = await response.json()
        setDiscoveredAgents(data)
        fetchStats()
      } else {
        setError('Exploration failed')
      }
    } catch (err) {
      console.error('Exploration failed:', err)
      setError('Network error during exploration')
    } finally {
      setIsExploring(false)
    }
  }

  const getReputationColor = (reputation: number) => {
    if (reputation >= 0.8) return 'text-green-600 dark:text-green-400'
    if (reputation >= 0.6) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  // Concept card
  const renderConceptCard = () => (
    <div className="card bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-700">
      <button
        onClick={() => setShowInfo(!showInfo)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-lg flex items-center justify-center">
            <Lightbulb className="text-green-600 dark:text-green-400" size={20} />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{t('network.whatIsNetwork')}</h3>
            <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('network.clickToLearnConcepts')}</p>
          </div>
        </div>
        {showInfo ? <ChevronUp size={20} className="text-secondary-400 dark:text-secondary-500" /> : <ChevronDown size={20} className="text-secondary-400 dark:text-secondary-500" />}
      </button>

      {showInfo && (
        <div className="mt-6 space-y-6">
          {/* Concept Definition */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Info size={16} className="text-green-500 dark:text-green-400" />
              {t('network.conceptDefinition')}
            </h4>
            <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed">
              {t('network.conceptDefinitionText')}
            </p>
          </div>

          {/* Use Cases */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-green-500 dark:text-green-400" />
              {t('network.useCases')}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {useCaseExamples.map((example, idx) => (
                <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                  <h5 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2">{example.title}</h5>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                  <div className="text-xs space-y-1">
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('network.scenario')}:</span>
                      <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('network.outcome')}:</span>
                      <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Exploration Dimensions */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Target size={16} className="text-purple-500" />
              {t('network.explorationDimensions')}
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('network.capabilityMatch')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('network.capabilityMatchDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('network.reputationScore')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('network.reputationScoreDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('network.networkDistance')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('network.networkDistanceDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('network.activeStatus')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('network.activeStatusDesc')}</p>
              </div>
            </div>
          </div>

          {/* Trust Network */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Shield size={16} className="text-blue-500 dark:text-blue-400" />
              {t('network.trustNetwork')}
            </h4>
            <div className="flex items-center gap-2 text-sm flex-wrap">
              <div className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-800 rounded-full">
                <span className="font-medium text-green-700 dark:text-green-300">{t('network.reputationThreshold')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-800 rounded-full">
                <span className="font-medium text-blue-700 dark:text-blue-300">{t('network.joinTrustNetwork')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-purple-100 dark:bg-purple-800 rounded-full">
                <span className="font-medium text-purple-700 dark:text-purple-300">{t('network.priorityRecommendation')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-800 rounded-full">
                <span className="font-medium text-yellow-700 dark:text-yellow-300">{t('network.fastMatching')}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderExploreView = () => (
    <div className="space-y-6">
      {renderConceptCard()}

      {/* Search Form */}
      <div className="card">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-blue-100 dark:bg-blue-800 rounded-xl flex items-center justify-center">
            <Search className="text-blue-600 dark:text-blue-400" size={24} />
          </div>
          <div>
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">Explore Network</h3>
            <p className="text-sm text-secondary-500 dark:text-secondary-400">Discover new agents in the network</p>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
              Target Capability
            </label>
            <input
              type="text"
              placeholder="e.g., data-processing, nlp, ml-training"
              className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
              value={targetCapability}
              onChange={(e) => setTargetCapability(e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Exploration Depth
              </label>
              <select className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100">
                <option value="1">1 hop</option>
                <option value="2">2 hops</option>
                <option value="3">3 hops</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                Max Agents
              </label>
              <select className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100">
                <option value="5">5 agents</option>
                <option value="10">10 agents</option>
                <option value="20">20 agents</option>
              </select>
            </div>
          </div>

          <button
            className="btn btn-primary w-full flex items-center justify-center gap-2"
            onClick={handleExplore}
            disabled={isExploring}
          >
            {isExploring ? (
              <RefreshCw className="animate-spin" size={18} />
            ) : (
              <Globe size={18} />
            )}
            {isExploring ? 'Exploring...' : 'Start Exploration'}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="card bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700">
          <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {/* Discovered Agents */}
      <div className="card">
        <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Discovered Agents</h3>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={24} />
            <span className="ml-2 text-secondary-500 dark:text-secondary-400">Loading agents...</span>
          </div>
        ) : discoveredAgents.length === 0 ? (
          <div className="text-center py-8 text-secondary-500 dark:text-secondary-400">
            <Network size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
            <p>No agents discovered yet.</p>
            <p className="text-sm">Start an exploration to find agents in the network.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {discoveredAgents.map((agent) => (
              <div
                key={agent.agent_id}
                className="flex items-center justify-between p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-600 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-800 rounded-lg flex items-center justify-center">
                    <Network className="text-blue-600 dark:text-blue-400" size={20} />
                  </div>
                  <div>
                    <p className="font-medium text-light-text-primary dark:text-secondary-100">{agent.agent_name}</p>
                    <p className="text-xs text-secondary-500 dark:text-secondary-400">
                      {agent.capabilities.slice(0, 2).join(', ') || 'No capabilities listed'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(agent.status)}`}>
                    {agent.status}
                  </span>
                  <span className={`text-sm font-semibold ${getReputationColor(agent.reputation)}`}>
                    {(agent.reputation * 100).toFixed(0)}%
                  </span>
                  <button className="btn btn-secondary btn-sm">
                    <UserPlus size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  const renderNetworkView = () => (
    <div className="space-y-6">
      {/* My Network */}
      <div className="card">
        <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">My Network</h3>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={24} />
            <span className="ml-2 text-secondary-500 dark:text-secondary-400">Loading...</span>
          </div>
        ) : discoveredAgents.length === 0 ? (
          <div className="text-center py-8 text-secondary-500 dark:text-secondary-400">
            <Users size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
            <p>No agents in your network yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {discoveredAgents.slice(0, 6).map((agent) => (
              <div key={agent.agent_id} className="p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <div className="w-10 h-10 bg-primary-100 dark:bg-primary-800 rounded-lg flex items-center justify-center">
                    <Users className="text-primary-600 dark:text-primary-400" size={20} />
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${getStatusColor(agent.status)}`}>
                    {agent.status}
                  </span>
                </div>
                <h4 className="font-medium text-light-text-primary dark:text-secondary-100">{agent.agent_name}</h4>
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-2">
                  {agent.capabilities.join(', ') || 'No capabilities listed'}
                </p>
                <div className="flex items-center gap-1">
                  <Star className="text-yellow-500 dark:text-yellow-400" size={14} />
                  <span className={`text-sm ${getReputationColor(agent.reputation)}`}>
                    {(agent.reputation * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  const renderTrustedView = () => {
    const trustedAgents = discoveredAgents.filter(a => a.reputation >= 0.7)

    return (
      <div className="space-y-6">
        {/* Trusted Agents */}
        <div className="card">
          <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Trusted Agents</h3>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={24} />
              <span className="ml-2 text-secondary-500 dark:text-secondary-400">Loading...</span>
            </div>
          ) : trustedAgents.length === 0 ? (
            <div className="text-center py-8 text-secondary-500 dark:text-secondary-400">
              <Star size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
              <p>No trusted agents yet.</p>
              <p className="text-sm">Agents with reputation above 70% will appear here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {trustedAgents.map((agent) => (
                <div
                  key={agent.agent_id}
                  className="flex items-center justify-between p-4 bg-green-50 dark:bg-green-900/30 rounded-lg border border-green-100 dark:border-green-700"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-green-100 dark:bg-green-800 rounded-full flex items-center justify-center">
                      <Users className="text-green-600 dark:text-green-400" size={24} />
                    </div>
                    <div>
                      <p className="font-semibold text-light-text-primary dark:text-secondary-100">{agent.agent_name}</p>
                      <p className="text-sm text-secondary-500 dark:text-secondary-400">
                        {agent.capabilities.join(', ') || 'No capabilities listed'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-green-600 dark:text-green-400 font-semibold">
                      {(agent.reputation * 100).toFixed(0)}%
                    </span>
                    <button className="btn btn-secondary btn-sm">
                      <MessageSquare size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  const renderRecommendationsView = () => (
    <div className="space-y-6">
      {/* Recommendations */}
      <div className="card">
        <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Network Recommendations</h3>
        <div className="mb-4">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Enter capability to search for recommendations"
              className="input flex-1 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
              value={targetCapability}
              onChange={(e) => setTargetCapability(e.target.value)}
            />
            <button
              className="btn btn-secondary"
              onClick={() => targetCapability && fetchRecommendations(targetCapability)}
              disabled={!targetCapability}
            >
              <Search size={18} />
            </button>
          </div>
        </div>
        {recommendations.length === 0 ? (
          <div className="text-center py-8 text-secondary-500 dark:text-secondary-400">
            <Target size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
            <p>No recommendations yet.</p>
            <p className="text-sm">Enter a capability above to get recommendations.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {recommendations.map((rec) => (
              <div
                key={rec.recommended_agent_id}
                className="flex items-center justify-between p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
                    <Star className="text-purple-600 dark:text-purple-400" size={24} />
                  </div>
                  <div>
                    <p className="font-semibold text-light-text-primary dark:text-secondary-100">{rec.recommended_agent_name}</p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">{rec.reason}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-xs text-secondary-500 dark:text-secondary-400">Match</p>
                    <p className={`font-semibold ${getReputationColor(rec.capability_match)}`}>
                      {(rec.capability_match * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-secondary-500 dark:text-secondary-400">Trust</p>
                    <p className={`font-semibold ${getReputationColor(rec.trust_score)}`}>
                      {(rec.trust_score * 100).toFixed(0)}%
                    </p>
                  </div>
                  <button className="btn btn-primary btn-sm">
                    <UserPlus size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">{t('network.title')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('network.exploreAgents')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium">
            {t('network.recommendations')}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-800 rounded-lg flex items-center justify-center">
              <Search className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{stats.total_explorations}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Explorations</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-lg flex items-center justify-center">
              <Users className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{stats.network_size}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Network Size</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
              <Star className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{stats.trusted_agents}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Trusted</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-800 rounded-lg flex items-center justify-center">
              <TrendingUp className="text-yellow-600 dark:text-yellow-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">{stats.total_discovered}</p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">Discovered</p>
            </div>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="border-b border-secondary-200 overflow-x-auto">
        <div className="flex gap-2 sm:gap-6 min-w-max">
          {[
            { value: 'explore', label: t('network.exploreAgents'), icon: Search },
            { value: 'network', label: t('network.trustedNetwork'), icon: Users },
            { value: 'trusted', label: t('network.connect'), icon: Shield },
            { value: 'recommendations', label: t('network.recommendations'), icon: Star },
          ].map((tab) => (
            <button
              key={tab.value}
              onClick={() => setViewMode(tab.value as ViewMode)}
              className={`flex items-center gap-1 sm:gap-2 px-2 sm:px-1 py-2 sm:py-3 border-b-2 transition-colors text-sm sm:text-base ${
                viewMode === tab.value
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-secondary-500 hover:text-secondary-700'
              }`}
            >
              <tab.icon size={16} className="sm:w-[18px] sm:h-[18px]" />
              <span className="hidden sm:inline">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      {viewMode === 'explore' && renderExploreView()}
      {viewMode === 'network' && renderNetworkView()}
      {viewMode === 'trusted' && renderTrustedView()}
      {viewMode === 'recommendations' && renderRecommendationsView()}
    </div>
  )
}
