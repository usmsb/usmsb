import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Search,
  ArrowRightLeft,
  MessageSquare,
  CheckCircle,
  Clock,
  Zap,
  Target,
  RefreshCw,
  Briefcase,
  AlertCircle,
  Info,
  Lightbulb,
  Users,
  TrendingUp,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { useAuthStore } from '../stores/authStore'
import { authFetch } from '@/lib/api'
import type {
  Opportunity,
  NegotiationSession,
  NegotiationRound,
  MatchStats,
  MatchingSearchResult,
} from '@/types'
import { transformToOpportunity, isNegotiationActive } from '@/types'
import { getStatusColor, getMatchScoreColor } from '@/utils/statusColors'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

type ViewMode = 'discover' | 'opportunities' | 'negotiations' | 'matches'
type SearchType = 'supply' | 'demand'

export default function ActiveMatching() {
  const { t } = useTranslation()
  const { agentId } = useAuthStore()

  // Use case examples with translations
  const useCaseExamples = [
    {
      title: t('matching.useCase1Title'),
      description: t('matching.useCase1Desc'),
      scenario: t('matching.useCase1Scenario'),
      outcome: t('matching.useCase1Outcome'),
    },
    {
      title: t('matching.useCase2Title'),
      description: t('matching.useCase2Desc'),
      scenario: t('matching.useCase2Scenario'),
      outcome: t('matching.useCase2Outcome'),
    },
    {
      title: t('matching.useCase3Title'),
      description: t('matching.useCase3Desc'),
      scenario: t('matching.useCase3Scenario'),
      outcome: t('matching.useCase3Outcome'),
    },
  ]
  const [viewMode, setViewMode] = useState<ViewMode>('discover')
  const [searchType, setSearchType] = useState<SearchType>('demand')
  const [opportunities, setOpportunities] = useState<Opportunity[]>([])
  const [negotiations, setNegotiations] = useState<NegotiationSession[]>([])
  const [, setSelectedOpportunity] = useState<Opportunity | null>(null)
  const [selectedNegotiation, setSelectedNegotiation] = useState<NegotiationSession | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showInfo, setShowInfo] = useState(false)
  const [stats, setStats] = useState<MatchStats>({
    total_opportunities: 0,
    active_negotiations: 0,
    successful_matches: 0,
    pending_responses: 0,
  })

  // Proactive Search Form
  const [searchForm, setSearchForm] = useState({
    capabilities: '',
    budget_min: '',
    budget_max: '',
    deadline: '',
    description: '',
  })

  // Fetch opportunities from API
  const fetchOpportunities = async () => {
    try {
      const response = await authFetch(`${API_BASE}/matching/opportunities`)
      if (response.ok) {
        const data: MatchingSearchResult[] = await response.json()
        const transformed: Opportunity[] = data.map((opp) => transformToOpportunity(opp))
        setOpportunities(transformed)
        setStats(prev => ({
          ...prev,
          total_opportunities: transformed.length,
        }))
      }
    } catch (err) {
      console.error('Failed to fetch opportunities:', err)
    }
  }

  // Fetch negotiations from API
  const fetchNegotiations = async () => {
    try {
      const response = await authFetch(`${API_BASE}/matching/negotiations`)
      if (response.ok) {
        const data: NegotiationSession[] = await response.json()
        setNegotiations(data)
        setStats(prev => ({
          ...prev,
          active_negotiations: data.filter(isNegotiationActive).length,
        }))
      }
    } catch (err) {
      console.error('Failed to fetch negotiations:', err)
    }
  }

  // Initial data fetch
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await Promise.all([fetchOpportunities(), fetchNegotiations()])
      setIsLoading(false)
    }
    loadData()
  }, [])

  // Reset search form when viewMode changes
  useEffect(() => {
    setSearchForm({
      capabilities: '',
      budget_min: '',
      budget_max: '',
      deadline: '',
      description: '',
    })
    setError(null)
  }, [viewMode])

  const handleProactiveSearch = async () => {
    setIsSearching(true)
    setError(null)

    try {
      const endpoint = searchType === 'demand'
        ? `${API_BASE}/matching/search-demands`
        : `${API_BASE}/matching/search-suppliers`

      const capabilities = searchForm.capabilities.split(',').map(s => s.trim()).filter(Boolean)
      const requestBody = searchType === 'demand'
        ? {
            agent_id: agentId || 'anonymous',
            capabilities,
            budget_min: searchForm.budget_min ? parseFloat(searchForm.budget_min) : undefined,
            budget_max: searchForm.budget_max ? parseFloat(searchForm.budget_max) : undefined,
          }
        : {
            agent_id: agentId || 'anonymous',
            required_skills: capabilities,
            budget_min: searchForm.budget_min ? parseFloat(searchForm.budget_min) : undefined,
            budget_max: searchForm.budget_max ? parseFloat(searchForm.budget_max) : undefined,
          }

      const response = await authFetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(requestBody),
      })

      if (response.ok) {
        const results: MatchingSearchResult[] = await response.json()
        const newOpportunities: Opportunity[] = results.map((item) => {
          const transformed = transformToOpportunity({
            ...item,
            opportunity_type: searchType,
            opportunity_id: item.opportunity_id || `opp-${Date.now()}-${Math.random()}`,
            status: 'discovered',
            created_at: Date.now(),
          })
          return transformed
        })
        setOpportunities(prev => [...newOpportunities, ...prev])
        setViewMode('opportunities')
      } else {
        setError('Search failed. Please try again.')
      }
    } catch (err) {
      setError('Network error. Please check your connection.')
      console.error('Search error:', err)
    } finally {
      setIsSearching(false)
    }
  }

  const handleInitiateNegotiation = async (opportunity: Opportunity) => {
    try {
      const response = await authFetch(`${API_BASE}/matching/negotiate`, {
        method: 'POST',
        body: JSON.stringify({
          initiator_id: agentId || 'anonymous',
          counterpart_id: opportunity.counterpart_agent_id,
          context: {
            ...opportunity.details,
            opportunity_id: opportunity.opportunity_id,
          },
        }),
      })

      if (response.ok) {
        const newNegotiation: NegotiationSession = await response.json()
        setNegotiations(prev => [newNegotiation, ...prev])
        setSelectedOpportunity(null)
        setViewMode('negotiations')
        setOpportunities(prev => prev.map(o =>
          o.opportunity_id === opportunity.opportunity_id
            ? { ...o, status: 'negotiating' as const }
            : o
        ))
      } else {
        setError('Failed to initiate negotiation')
      }
    } catch (err) {
      setError('Network error')
      console.error('Negotiation error:', err)
    }
  }

  // Concept card
  const renderConceptCard = () => (
    <div className="card bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/30 dark:to-blue-900/30 border border-primary-200 dark:border-primary-700">
      <button
        onClick={() => setShowInfo(!showInfo)}
        className="w-full flex items-center justify-between"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-100 dark:bg-primary-800 rounded-lg flex items-center justify-center">
            <Lightbulb className="text-primary-600 dark:text-primary-400" size={20} />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{t('matching.whatIsMatching')}</h3>
            <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('matching.clickToLearnConcepts')}</p>
          </div>
        </div>
        {showInfo ? <ChevronUp size={20} className="text-secondary-400 dark:text-secondary-500" /> : <ChevronDown size={20} className="text-secondary-400 dark:text-secondary-500" />}
      </button>

      {showInfo && (
        <div className="mt-6 space-y-6">
          {/* Concept Definition */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Info size={16} className="text-primary-500" />
              {t('matching.conceptDefinition')}
            </h4>
            <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed">
              {t('matching.conceptDefinitionText')}
            </p>
          </div>

          {/* Use Cases */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <TrendingUp size={16} className="text-green-500" />
              {t('matching.useCases')}
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {useCaseExamples.map((example, idx) => (
                <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                  <h5 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2">{example.title}</h5>
                  <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                  <div className="text-xs space-y-1">
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('matching.scenario')}:</span>
                      <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                    </div>
                    <div className="flex gap-2">
                      <span className="text-secondary-500 dark:text-secondary-400">{t('matching.outcome')}:</span>
                      <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Matching Dimensions */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Target size={16} className="text-purple-500" />
              {t('matching.matchingDimensions')}
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('matching.capabilityMatch')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('matching.capabilityMatchDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('matching.priceMatch')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('matching.priceMatchDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('matching.reputationMatch')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('matching.reputationMatchDesc')}</p>
              </div>
              <div className="p-3 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 text-center">
                <p className="text-xs text-secondary-500 dark:text-secondary-400 mb-1">{t('matching.timeMatch')}</p>
                <p className="text-sm text-secondary-700 dark:text-secondary-300">{t('matching.timeMatchDesc')}</p>
              </div>
            </div>
          </div>

          {/* Matching Process */}
          <div>
            <h4 className="font-medium text-light-text-primary dark:text-secondary-100 mb-2 flex items-center gap-2">
              <Users size={16} className="text-blue-500" />
              {t('matching.matchingProcess')}
            </h4>
            <div className="flex items-center gap-2 text-sm flex-wrap">
              <div className="flex items-center gap-1 px-3 py-1.5 bg-primary-100 dark:bg-primary-900/50 rounded-full">
                <span className="font-medium text-primary-700 dark:text-primary-300">{t('matching.stepPublishService')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/50 rounded-full">
                <span className="font-medium text-green-700 dark:text-green-300">{t('matching.stepSmartMatch')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-purple-100 dark:bg-purple-900/50 rounded-full">
                <span className="font-medium text-purple-700 dark:text-purple-300">{t('matching.stepNegotiate')}</span>
              </div>
              <span className="text-secondary-400 dark:text-secondary-500">→</span>
              <div className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/50 rounded-full">
                <span className="font-medium text-yellow-700 dark:text-yellow-300">{t('matching.stepDeal')}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )

  const renderDiscoverView = () => (
    <div className="space-y-6">
      {renderConceptCard()}

      {/* Proactive Search Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Supply Search Card */}
        <div className="card border-2 border-primary-200 dark:border-primary-700 bg-gradient-to-br from-primary-50 to-white dark:from-primary-900/20 dark:to-secondary-800">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-primary-100 dark:bg-primary-800 rounded-xl flex items-center justify-center">
              <Briefcase className="text-primary-600 dark:text-primary-400" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{t('onboarding.asSupplier')}</h3>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('dashboard.findDemanders')}</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('agents.capabilities')}
              </label>
              <input
                type="text"
                placeholder={t('agents.searchPlaceholder')}
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                value={searchType === 'supply' ? searchForm.capabilities : ''}
                onChange={(e) =>
                  setSearchForm({ ...searchForm, capabilities: e.target.value })
                }
                onFocus={() => setSearchType('supply')}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publish.demand.budgetMin')}
                </label>
                <input
                  type="number"
                  placeholder="$0"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  value={searchType === 'supply' ? searchForm.budget_min : ''}
                  onChange={(e) =>
                    setSearchForm({ ...searchForm, budget_min: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publish.demand.budgetMax')}
                </label>
                <input
                  type="number"
                  placeholder="$10000"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  value={searchType === 'supply' ? searchForm.budget_max : ''}
                  onChange={(e) =>
                    setSearchForm({ ...searchForm, budget_max: e.target.value })
                  }
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('publish.service.description')}
              </label>
              <textarea
                placeholder={t('agents.noAgents')}
                className="input min-h-[80px] dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                value={searchType === 'supply' ? searchForm.description : ''}
                onChange={(e) =>
                  setSearchForm({ ...searchForm, description: e.target.value })
                }
              />
            </div>

            <button
              className="btn btn-primary w-full flex items-center justify-center gap-2"
              onClick={() => {
                setSearchType('supply')
                handleProactiveSearch()
              }}
              disabled={isSearching}
            >
              {isSearching && searchType === 'supply' ? (
                <RefreshCw className="animate-spin" size={18} />
              ) : (
                <Search size={18} />
              )}
              {isSearching && searchType === 'supply'
                ? t('common.loading')
                : t('dashboard.findSuppliers')}
            </button>
          </div>
        </div>

        {/* Demand Search Card */}
        <div className="card border-2 border-green-200 dark:border-green-700 bg-gradient-to-br from-green-50 to-white dark:from-green-900/20 dark:to-secondary-800">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-12 h-12 bg-green-100 dark:bg-green-800 rounded-xl flex items-center justify-center">
              <Target className="text-green-600 dark:text-green-400" size={24} />
            </div>
            <div>
              <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">{t('onboarding.asDemander')}</h3>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('dashboard.findSuppliers')}</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('publish.demand.requiredSkills')}
              </label>
              <input
                type="text"
                placeholder={t('agents.searchPlaceholder')}
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                value={searchType === 'demand' ? searchForm.capabilities : ''}
                onChange={(e) =>
                  setSearchForm({ ...searchForm, capabilities: e.target.value })
                }
                onFocus={() => setSearchType('demand')}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publish.demand.budgetMin')}
                </label>
                <input
                  type="number"
                  placeholder="$0"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  value={searchType === 'demand' ? searchForm.budget_min : ''}
                  onChange={(e) =>
                    setSearchForm({ ...searchForm, budget_min: e.target.value })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                  {t('publish.demand.budgetMax')}
                </label>
                <input
                  type="number"
                  placeholder="$10000"
                  className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                  value={searchType === 'demand' ? searchForm.budget_max : ''}
                  onChange={(e) =>
                    setSearchForm({ ...searchForm, budget_max: e.target.value })
                  }
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('publish.demand.deadline')}
              </label>
              <input
                type="date"
                className="input dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100"
                value={searchType === 'demand' ? searchForm.deadline : ''}
                onChange={(e) =>
                  setSearchForm({ ...searchForm, deadline: e.target.value })
                }
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-secondary-700 dark:text-secondary-300 mb-1">
                {t('publish.demand.description')}
              </label>
              <textarea
                placeholder={t('agents.noAgents')}
                className="input min-h-[80px] dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
                value={searchType === 'demand' ? searchForm.description : ''}
                onChange={(e) =>
                  setSearchForm({ ...searchForm, description: e.target.value })
                }
              />
            </div>

            <button
              className="btn btn-primary w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700"
              onClick={() => {
                setSearchType('demand')
                handleProactiveSearch()
              }}
              disabled={isSearching}
            >
              {isSearching && searchType === 'demand' ? (
                <RefreshCw className="animate-spin" size={18} />
              ) : (
                <Search size={18} />
              )}
              {isSearching && searchType === 'demand'
                ? t('common.loading')
                : t('dashboard.findDemanders')}
            </button>
          </div>
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div className="p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg flex items-center gap-2 text-red-700 dark:text-red-400">
          <AlertCircle size={20} />
          {error}
        </div>
      )}

      {/* Recent Activity */}
      <div className="card">
        <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Recent Activity</h3>
        {isLoading ? (
          <div className="flex items-center justify-center h-24">
            <RefreshCw className="animate-spin text-secondary-400 dark:text-secondary-500" size={24} />
          </div>
        ) : opportunities.length === 0 ? (
          <div className="text-center text-secondary-500 dark:text-secondary-400 py-8">
            <Search size={48} className="mx-auto mb-3 opacity-50" />
            <p>No opportunities found. Start a search to discover matches!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {opportunities.slice(0, 3).map((opp) => (
              <div
                key={opp.opportunity_id}
                className="flex items-center justify-between p-3 bg-secondary-50 dark:bg-secondary-700 rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      opp.opportunity_type === 'demand' ? 'bg-green-500' : 'bg-primary-500'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-medium text-light-text-primary dark:text-secondary-100">
                      {opp.counterpart_name}
                    </p>
                    <p className="text-xs text-secondary-500 dark:text-secondary-400">
                      {opp.opportunity_type === 'demand' ? 'Looking for services' : 'Offering services'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-sm font-semibold ${getMatchScoreColor(opp.match_score.overall)}`}
                  >
                    {(opp.match_score.overall * 100).toFixed(0)}% match
                  </span>
                  <span
                    className={`px-2 py-1 rounded-full text-xs ${getStatusColor(opp.status)}`}
                  >
                    {opp.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )

  const renderOpportunitiesView = () => (
    <div className="space-y-6">
      {/* Filters */}
      <div className="card">
        <div className="flex flex-col md:flex-row gap-4">
          <div className="flex-1 relative">
            <Search
              className="absolute left-3 top-1/2 -translate-y-1/2 text-secondary-400 dark:text-secondary-500"
              size={20}
            />
            <input
              type="text"
              placeholder="Search opportunities..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input pl-10 dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100 dark:placeholder-secondary-400"
            />
          </div>
          <select className="input w-auto dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100">
            <option value="all">All Types</option>
            <option value="supply">Suppliers</option>
            <option value="demand">Demanders</option>
          </select>
          <select className="input w-auto dark:bg-secondary-700 dark:border-secondary-600 dark:text-secondary-100">
            <option value="all">All Status</option>
            <option value="discovered">Discovered</option>
            <option value="contacted">Contacted</option>
            <option value="negotiating">Negotiating</option>
          </select>
        </div>
      </div>

      {/* Opportunities List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="animate-spin text-secondary-400 dark:text-secondary-500" size={32} />
        </div>
      ) : opportunities.length === 0 ? (
        <div className="card text-center text-secondary-500 dark:text-secondary-400 py-12">
          <Target size={48} className="mx-auto mb-3 opacity-50" />
          <p>No opportunities available.</p>
          <p className="text-sm mt-2">Use the Discover tab to search for matches.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {opportunities.map((opp) => (
            <div key={opp.opportunity_id} className="card hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      opp.opportunity_type === 'demand'
                        ? 'bg-green-100 dark:bg-green-800'
                        : 'bg-primary-100 dark:bg-primary-800'
                    }`}
                  >
                    {opp.opportunity_type === 'demand' ? (
                      <Target className="text-green-600 dark:text-green-400" size={20} />
                    ) : (
                      <Briefcase className="text-primary-600 dark:text-primary-400" size={20} />
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">
                      {opp.counterpart_name}
                    </h3>
                    <p className="text-xs text-secondary-500 dark:text-secondary-400">
                      {opp.opportunity_type === 'demand' ? 'Potential Customer' : 'Service Provider'}
                    </p>
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(opp.status)}`}>
                  {opp.status}
                </span>
              </div>

              {/* Match Score */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-secondary-600 dark:text-secondary-400">Match Score</span>
                  <span
                    className={`text-lg font-bold ${getMatchScoreColor(opp.match_score.overall)}`}
                  >
                    {(opp.match_score.overall * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 bg-secondary-100 dark:bg-secondary-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      opp.match_score.overall >= 0.8
                        ? 'bg-green-500'
                        : opp.match_score.overall >= 0.6
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${opp.match_score.overall * 100}%` }}
                  />
                </div>
              </div>

              {/* Score Breakdown */}
              <div className="grid grid-cols-4 gap-2 mb-4">
                <div className="text-center p-2 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                  <p className="text-xs text-secondary-500 dark:text-secondary-400">Capability</p>
                  <p className="text-sm font-semibold text-light-text-primary dark:text-secondary-100">
                    {(opp.match_score.capability_match * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="text-center p-2 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                  <p className="text-xs text-secondary-500 dark:text-secondary-400">Price</p>
                  <p className="text-sm font-semibold text-light-text-primary dark:text-secondary-100">
                    {(opp.match_score.price_match * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="text-center p-2 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                  <p className="text-xs text-secondary-500 dark:text-secondary-400">Reputation</p>
                  <p className="text-sm font-semibold text-light-text-primary dark:text-secondary-100">
                    {(opp.match_score.reputation_match * 100).toFixed(0)}%
                  </p>
                </div>
                <div className="text-center p-2 bg-secondary-50 dark:bg-secondary-700 rounded-lg">
                  <p className="text-xs text-secondary-500 dark:text-secondary-400">Time</p>
                  <p className="text-sm font-semibold text-light-text-primary dark:text-secondary-100">
                    {(opp.match_score.time_match * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              {/* Details */}
              <div className="text-sm text-secondary-600 dark:text-secondary-400 mb-4">
                {opp.match_score.reasoning}
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <button
                  className="btn btn-secondary flex-1"
                  onClick={() => setSelectedOpportunity(opp)}
                >
                  View Details
                </button>
                {opp.status === 'discovered' && (
                  <button
                    className="btn btn-primary flex-1"
                    onClick={() => handleInitiateNegotiation(opp)}
                  >
                    Start Negotiation
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )

  const renderNegotiationsView = () => (
    <div className="space-y-6">
      {negotiations.length === 0 ? (
        <div className="card text-center text-secondary-500 py-12">
          <MessageSquare size={48} className="mx-auto mb-3 opacity-50" />
          <p>No active negotiations.</p>
          <p className="text-sm mt-2">Start a negotiation from an opportunity.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Negotiation List */}
          <div className="space-y-4">
            {negotiations.map((neg) => (
              <div
                key={neg.session_id}
                className={`card cursor-pointer transition-all ${
                  selectedNegotiation?.session_id === neg.session_id
                    ? 'ring-2 ring-primary-500'
                    : 'hover:shadow-md'
                }`}
                onClick={() => setSelectedNegotiation(neg)}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
                      <MessageSquare className="text-purple-600 dark:text-purple-400" size={20} />
                    </div>
                    <div>
                      <h3 className="font-semibold text-light-text-primary dark:text-secondary-100">
                        {(neg.context?.service as string) || 'Service Negotiation'}
                      </h3>
                      <p className="text-xs text-secondary-500 dark:text-secondary-400">
                        with {neg.counterpart_id}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(neg.status)}`}>
                    {neg.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-sm text-secondary-600">
                  <div className="flex items-center gap-1">
                    <ArrowRightLeft size={14} />
                    <span>{neg.rounds?.length || 0} rounds</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={14} />
                    <span>{new Date(neg.created_at * 1000 || neg.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Negotiation Detail */}
          {selectedNegotiation ? (
            <div className="card">
              <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">
                Negotiation Details
              </h3>

              {/* Rounds */}
              {selectedNegotiation.rounds && selectedNegotiation.rounds.length > 0 ? (
                <div className="space-y-4 mb-6">
                  {selectedNegotiation.rounds.map((round: NegotiationRound, idx: number) => (
                    <div key={idx} className="border rounded-lg p-4">
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-sm font-medium text-secondary-700">
                          Round {round.round_number || idx + 1}
                        </span>
                        <span
                          className={`px-2 py-1 rounded-full text-xs ${getStatusColor(round.response)}`}
                        >
                          {round.response || 'pending'}
                        </span>
                      </div>

                      {round.proposal && (
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-secondary-500">Price</p>
                            <p className="font-medium">${round.proposal.price}</p>
                          </div>
                          <div>
                            <p className="text-secondary-500">Delivery</p>
                            <p className="font-medium">{round.proposal.delivery_time}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-secondary-500 text-center py-8 mb-6">
                  No negotiation rounds yet
                </div>
              )}

              {/* Completed Negotiation */}
              {selectedNegotiation.status === 'agreed' && selectedNegotiation.final_terms && (
                <div className="bg-green-50 dark:bg-green-900/30 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
                    <span className="font-medium text-green-700 dark:text-green-400">Deal Closed!</span>
                  </div>
                  <div className="text-sm text-green-700 dark:text-green-300">
                    <p>Final Price: ${selectedNegotiation.final_terms.price}</p>
                    <p>Delivery: {selectedNegotiation.final_terms.delivery_time}</p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="card flex items-center justify-center h-64 text-secondary-500">
              Select a negotiation to view details
            </div>
          )}
        </div>
      )}
    </div>
  )

  const renderMatchesView = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Successful Matches */}
        <div className="card bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-700">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle className="text-green-600 dark:text-green-400" size={24} />
            <div>
              <h3 className="font-semibold text-green-900 dark:text-green-300">Successful Matches</h3>
              <p className="text-2xl font-bold text-green-700 dark:text-green-400">{stats.successful_matches}</p>
            </div>
          </div>
          <p className="text-sm text-green-600 dark:text-green-400">Deals closed this month</p>
        </div>

        {/* Active Negotiations */}
        <div className="card bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700">
          <div className="flex items-center gap-3 mb-3">
            <MessageSquare className="text-blue-600 dark:text-blue-400" size={24} />
            <div>
              <h3 className="font-semibold text-blue-900 dark:text-blue-300">Active Negotiations</h3>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-400">{stats.active_negotiations}</p>
            </div>
          </div>
          <p className="text-sm text-blue-600 dark:text-blue-400">Currently in progress</p>
        </div>

        {/* Pending Responses */}
        <div className="card bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-700">
          <div className="flex items-center gap-3 mb-3">
            <Clock className="text-yellow-600 dark:text-yellow-400" size={24} />
            <div>
              <h3 className="font-semibold text-yellow-900 dark:text-yellow-300">Pending Responses</h3>
              <p className="text-2xl font-bold text-yellow-700 dark:text-yellow-400">{stats.pending_responses}</p>
            </div>
          </div>
          <p className="text-sm text-yellow-600 dark:text-yellow-400">Awaiting counterparty</p>
        </div>
      </div>

      {/* Match History */}
      <div className="card">
        <h3 className="font-semibold text-light-text-primary dark:text-secondary-100 mb-4">Match History</h3>
        <div className="text-center text-secondary-500 dark:text-secondary-400 py-8">
          <CheckCircle size={48} className="mx-auto mb-3 opacity-50" />
          <p>No completed matches yet.</p>
          <p className="text-sm mt-2">Complete negotiations to see your match history.</p>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-light-text-primary dark:text-secondary-100">{t('matching.title')}</h1>
          <p className="text-sm md:text-base text-secondary-500 dark:text-secondary-400">
            {t('matching.searchSuppliers')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-green-100 dark:bg-green-800 text-green-700 dark:text-green-300 rounded-full text-sm font-medium">
            {t('matching.sendQuote')}
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
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {stats.total_opportunities}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('matching.title')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
              <MessageSquare className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {stats.active_negotiations}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('common.search')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-lg flex items-center justify-center">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {stats.successful_matches}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('common.success')}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-100 dark:bg-yellow-800 rounded-lg flex items-center justify-center">
              <Clock className="text-yellow-600 dark:text-yellow-400" size={20} />
            </div>
            <div>
              <p className="text-2xl font-bold text-light-text-primary dark:text-secondary-100">
                {stats.pending_responses}
              </p>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('common.loading')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* View Tabs */}
      <div className="border-b border-secondary-200 overflow-x-auto">
        <div className="flex gap-2 sm:gap-6 min-w-max">
          {[
            { value: 'discover', label: t('matching.discover'), icon: Zap },
            { value: 'opportunities', label: t('matching.opportunities'), icon: Target },
            { value: 'negotiations', label: t('matching.negotiations'), icon: MessageSquare },
            { value: 'matches', label: t('matching.matches'), icon: CheckCircle },
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
      {viewMode === 'discover' && renderDiscoverView()}
      {viewMode === 'opportunities' && renderOpportunitiesView()}
      {viewMode === 'negotiations' && renderNegotiationsView()}
      {viewMode === 'matches' && renderMatchesView()}
    </div>
  )
}
