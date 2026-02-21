import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import {
  Scale,
  Plus,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  ThumbsUp,
  ThumbsDown,
  AlertCircle,
  RefreshCw,
  Info,
  Lightbulb,
  TrendingUp,
  Target,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import clsx from 'clsx'
import { useAuthStore } from '../stores/authStore'
import { toast } from '../stores/toastStore'
import { getStatusColor } from '@/utils/statusColors'

const API_BASE = import.meta.env.VITE_API_URL || '/api'

// Use i18n for use cases
const getUseCaseExamples = (t: (key: string) => string) => [
  {
    title: t('governance.useCase1Title'),
    description: t('governance.useCase1Desc'),
    scenario: t('governance.useCase1Scenario'),
    outcome: t('governance.useCase1Outcome'),
  },
  {
    title: t('governance.useCase2Title'),
    description: t('governance.useCase2Desc'),
    scenario: t('governance.useCase2Scenario'),
    outcome: t('governance.useCase2Outcome'),
  },
  {
    title: t('governance.useCase3Title'),
    description: t('governance.useCase3Desc'),
    scenario: t('governance.useCase3Scenario'),
    outcome: t('governance.useCase3Outcome'),
  },
]

interface Proposal {
  id: string
  title: string
  description: string
  status: string
  votes_for: number
  votes_against: number
  quorum: number
  deadline: string
  proposer_id: string
  created_at?: number
}

interface GovernanceStats {
  total_proposals: number
  active_proposals: number
  total_votes: number
  participation_rate: number
}

export default function Governance() {
  const { t } = useTranslation()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [selectedProposal, setSelectedProposal] = useState<Proposal | null>(null)
  const [proposals, setProposals] = useState<Proposal[]>([])
  const [stats, setStats] = useState<GovernanceStats>({
    total_proposals: 0,
    active_proposals: 0,
    total_votes: 0,
    participation_rate: 0,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { accessToken, agentId } = useAuthStore()

  // Fetch voting power from API
  const { data: votingPowerData } = useQuery<{ voting_power: number }>({
    queryKey: ['voting-power', agentId],
    queryFn: async () => {
      const headers: HeadersInit = {}
      if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`
      }
      const response = await fetch(`${API_BASE}/governance/voting-power`, {
        headers,
      })
      if (!response.ok) {
        // Return default voting power if not authenticated or endpoint not available
        return { voting_power: 0 }
      }
      return response.json()
    },
    enabled: true,
  })

  const votingPower = votingPowerData?.voting_power ?? 0

  // Fetch proposals and stats on mount
  useEffect(() => {
    fetchProposals()
    fetchStats()
  }, [])

  const fetchProposals = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_BASE}/governance/proposals`)
      if (response.ok) {
        const data = await response.json()
        setProposals(data)
      } else {
        setError('Failed to fetch proposals')
      }
    } catch (err) {
      console.error('Failed to fetch proposals:', err)
      setError('Network error. Please check if the backend is running.')
    } finally {
      setIsLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/governance/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const handleCreateProposal = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const form = e.currentTarget
    const formData = new FormData(form)
    const title = formData.get('title') as string
    const description = formData.get('description') as string

    if (!accessToken) {
      toast.error('Please connect your wallet first')
      return
    }

    try {
      const response = await fetch(`${API_BASE}/governance/proposals`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          title,
          description,
          proposal_type: 'community_initiative',
          proposer_id: agentId || 'anonymous',
          changes: {},
          tags: [],
        }),
      })

      if (response.ok) {
        setShowCreateModal(false)
        fetchProposals()
        fetchStats()
        form.reset()
        toast.success('Proposal created successfully')
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to create proposal')
      }
    } catch (err) {
      console.error('Failed to create proposal:', err)
      toast.error('Network error')
    }
  }

  const handleVote = async (proposalId: string, support: boolean) => {
    if (!accessToken) {
      toast.error('Please connect your wallet first')
      return
    }

    try {
      const response = await fetch(`${API_BASE}/governance/proposals/${proposalId}/vote`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          voter_id: agentId || 'anonymous',
          support,
          reason: '',
        }),
      })

      if (response.ok) {
        fetchProposals()
        fetchStats()
        setSelectedProposal(null)
        toast.success('Vote cast successfully')
      } else {
        const errorData = await response.json()
        toast.error(errorData.detail || 'Failed to cast vote')
      }
    } catch (err) {
      console.error('Failed to cast vote:', err)
      toast.error('Network error')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="text-green-500 dark:text-green-400" size={20} />
      case 'rejected':
        return <XCircle className="text-red-500 dark:text-red-400" size={20} />
      case 'active':
      case 'voting':
        return <Clock className="text-blue-500 dark:text-blue-400" size={20} />
      default:
        return <AlertCircle className="text-secondary-400 dark:text-secondary-500" size={20} />
    }
  }

  const totalVotes = (proposal: Proposal) => proposal.votes_for + proposal.votes_against
  const forPercentage = (proposal: Proposal) =>
    totalVotes(proposal) > 0 ? (proposal.votes_for / totalVotes(proposal)) * 100 : 0

  const activeProposals = proposals.filter((p) => p.status === 'active' || p.status === 'voting').length
  const passedProposals = proposals.filter((p) => p.status === 'passed').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl md:text-2xl font-bold text-secondary-900 dark:text-secondary-100">{t('governance.title')}</h1>
          <p className="text-sm md:text-base text-secondary-500">{t('governance.participate')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchProposals}
            className="btn btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={18} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn btn-primary flex items-center gap-2"
          >
            <Plus size={20} />
            <span className="hidden sm:inline">{t('governance.newProposal')}</span>
            <span className="sm:hidden">{t('common.create')}</span>
          </button>
        </div>
      </div>

      {/* 概念说明卡片 */}
      <div className="card bg-gradient-to-r from-amber-50 to-yellow-50 dark:from-amber-900/30 dark:to-yellow-900/30 border border-amber-200 dark:border-amber-700">
        <button
          onClick={() => setShowInfo(!showInfo)}
          className="w-full flex items-center justify-between"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-amber-100 dark:bg-amber-800 rounded-lg flex items-center justify-center">
              <Lightbulb className="text-amber-600 dark:text-amber-400" size={20} />
            </div>
            <div className="text-left">
              <h3 className="font-semibold text-secondary-900 dark:text-secondary-100">{t('governance.whatIsGovernance')}</h3>
              <p className="text-sm text-secondary-600 dark:text-secondary-400">{t('governance.clickToLearnConcepts')}</p>
            </div>
          </div>
          {showInfo ? <ChevronUp size={20} className="text-secondary-400 dark:text-secondary-500" /> : <ChevronDown size={20} className="text-secondary-400 dark:text-secondary-500" />}
        </button>

        {showInfo && (
          <div className="mt-6 space-y-6">
            <div>
              <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
                <Info size={16} className="text-amber-500 dark:text-amber-400" />
                {t('governance.conceptDefinition')}
              </h4>
              <p className="text-secondary-700 dark:text-secondary-300 leading-relaxed">
                {t('governance.conceptDefinitionText')}
              </p>
            </div>

            <div>
              <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
                <TrendingUp size={16} className="text-amber-500 dark:text-amber-400" />
                {t('governance.useCases')}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {getUseCaseExamples(t).map((example, idx) => (
                  <div key={idx} className="p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700">
                    <h5 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2">{example.title}</h5>
                    <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">{example.description}</p>
                    <div className="text-xs space-y-1">
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('governance.scenario')}:</span>
                        <span className="text-secondary-700 dark:text-secondary-300">{example.scenario}</span>
                      </div>
                      <div className="flex gap-2">
                        <span className="text-secondary-500 dark:text-secondary-400">{t('governance.outcome')}:</span>
                        <span className="text-green-600 dark:text-green-400">{example.outcome}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-secondary-900 dark:text-secondary-100 mb-2 flex items-center gap-2">
                <Target size={16} className="text-amber-500 dark:text-amber-400" />
                {t('governance.governanceProcess')}
              </h4>
              <div className="flex items-center gap-2 text-sm flex-wrap">
                <div className="flex items-center gap-1 px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 rounded-full">
                  <span className="font-medium text-blue-700 dark:text-blue-400">{t('governance.stepInitiate')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-full">
                  <span className="font-medium text-yellow-700 dark:text-yellow-400">{t('governance.stepDiscuss')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-full">
                  <span className="font-medium text-purple-700 dark:text-purple-400">{t('governance.stepVote')}</span>
                </div>
                <span className="text-secondary-400">→</span>
                <div className="flex items-center gap-1 px-3 py-1.5 bg-green-100 dark:bg-green-900/30 rounded-full">
                  <span className="font-medium text-green-700 dark:text-green-400">{t('governance.stepExecute')}</span>
                </div>
              </div>
            </div>
          </div>
        )}
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

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-100 dark:bg-blue-800 rounded-lg flex items-center justify-center">
              <Clock className="text-blue-600 dark:text-blue-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('governance.activeProposals')}</p>
              <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{activeProposals}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-100 dark:bg-green-800 rounded-lg flex items-center justify-center">
              <CheckCircle className="text-green-600 dark:text-green-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('governance.passed')}</p>
              <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{passedProposals}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-purple-100 dark:bg-purple-800 rounded-lg flex items-center justify-center">
              <Users className="text-purple-600 dark:text-purple-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('governance.totalVoters')}</p>
              <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{stats.total_votes.toLocaleString()}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-orange-100 dark:bg-orange-800 rounded-lg flex items-center justify-center">
              <Scale className="text-orange-600 dark:text-orange-400" size={20} />
            </div>
            <div>
              <p className="text-sm text-secondary-500 dark:text-secondary-400">{t('governance.yourVotingPower')}</p>
              <p className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{votingPower.toLocaleString()}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Proposals list */}
      <div className="card">
        <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100 mb-4">{t('governance.proposals')}</h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="animate-spin text-primary-500 dark:text-primary-400" size={24} />
            <span className="ml-2 text-secondary-500 dark:text-secondary-400">Loading proposals...</span>
          </div>
        ) : proposals.length === 0 ? (
          <div className="text-center py-8 text-secondary-500 dark:text-secondary-400">
            <Scale size={48} className="mx-auto mb-3 text-secondary-300 dark:text-secondary-600" />
            <p>No proposals yet.</p>
            <p className="text-sm">Create a new proposal to start governance.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {proposals.map((proposal) => (
              <div
                key={proposal.id}
                className="p-4 bg-secondary-50 dark:bg-secondary-700 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-600 cursor-pointer transition-colors"
                onClick={() => setSelectedProposal(proposal)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(proposal.status)}
                    <div>
                      <h3 className="font-medium text-secondary-900 dark:text-secondary-100">{proposal.title}</h3>
                      <p className="text-sm text-secondary-500 dark:text-secondary-400">by {proposal.proposer_id}</p>
                    </div>
                  </div>
                  <span
                    className={clsx(
                      'px-3 py-1 rounded-full text-sm font-medium',
                      getStatusColor(proposal.status)
                    )}
                  >
                    {proposal.status}
                  </span>
                </div>

                <p className="text-sm text-secondary-600 dark:text-secondary-300 mb-4">{proposal.description}</p>

                {(proposal.status === 'active' || proposal.status === 'voting') && (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-secondary-500 dark:text-secondary-400">Votes</span>
                      <span className="text-secondary-900 dark:text-secondary-100 font-medium">
                        {forPercentage(proposal).toFixed(1)}% For
                      </span>
                    </div>
                    <div className="w-full bg-secondary-200 dark:bg-secondary-600 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{ width: `${forPercentage(proposal)}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-secondary-500 dark:text-secondary-400">
                      <span>
                        <ThumbsUp size={12} className="inline mr-1" />
                        {proposal.votes_for.toLocaleString()}
                      </span>
                      <span>
                        <ThumbsDown size={12} className="inline mr-1" />
                        {proposal.votes_against.toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}

                {proposal.status !== 'active' && proposal.status !== 'voting' && (
                  <div className="flex items-center gap-4 text-sm text-secondary-500 dark:text-secondary-400">
                    <span>
                      <ThumbsUp size={14} className="inline mr-1 text-green-500 dark:text-green-400" />
                      {proposal.votes_for.toLocaleString()}
                    </span>
                    <span>
                      <ThumbsDown size={14} className="inline mr-1 text-red-500 dark:text-red-400" />
                      {proposal.votes_against.toLocaleString()}
                    </span>
                    <span>Deadline: {proposal.deadline}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="create-proposal-title">
          <form onSubmit={handleCreateProposal} className="bg-white dark:bg-secondary-800 rounded-xl p-6 w-full max-w-lg">
            <h2 id="create-proposal-title" className="text-xl font-bold text-secondary-900 dark:text-secondary-100 mb-4">{t('governance.createNewProposal')}</h2>
            <div className="space-y-4">
              <div>
                <label className="label">{t('governance.proposalTitle')}</label>
                <input name="title" type="text" className="input" placeholder={t('governance.proposalTitle')} required />
              </div>
              <div>
                <label className="label">{t('governance.description')}</label>
                <textarea name="description" className="input" rows={4} placeholder={t('governance.description')} required />
              </div>
              <div>
                <label className="label">{t('governance.votingPeriod')}</label>
                <input name="voting_period" type="number" className="input" defaultValue={7} min={1} max={30} />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button type="button" onClick={() => setShowCreateModal(false)} className="btn btn-secondary">
                {t('governance.cancel')}
              </button>
              <button type="submit" className="btn btn-primary">{t('governance.createProposal')}</button>
            </div>
          </form>
        </div>
      )}

      {/* Detail Modal */}
      {selectedProposal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true" aria-labelledby="proposal-detail-title">
          <div className="bg-white dark:bg-secondary-800 rounded-xl p-6 w-full max-w-2xl relative">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h2 id="proposal-detail-title" className="text-xl font-bold text-secondary-900 dark:text-secondary-100">{selectedProposal.title}</h2>
                <p className="text-sm text-secondary-500">Proposed by {selectedProposal.proposer_id}</p>
              </div>
              <span
                className={clsx(
                  'px-3 py-1 rounded-full text-sm font-medium',
                  getStatusColor(selectedProposal.status)
                )}
              >
                {selectedProposal.status}
              </span>
            </div>

            <p className="text-secondary-600 mb-6">{selectedProposal.description}</p>

            {(selectedProposal.status === 'active' || selectedProposal.status === 'voting') && (
              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <span className="font-medium text-secondary-900 dark:text-secondary-100">{t('governance.currentResults')}</span>
                  <span className="text-secondary-500">
                    {t('governance.quorum')}: {(selectedProposal.quorum * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-secondary-200 rounded-full h-4 mb-2">
                  <div
                    className="bg-green-500 h-4 rounded-full"
                    style={{ width: `${forPercentage(selectedProposal)}%` }}
                  />
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-green-600 font-medium">
                    {selectedProposal.votes_for.toLocaleString()} {t('governance.for')}
                  </span>
                  <span className="text-red-600 font-medium">
                    {selectedProposal.votes_against.toLocaleString()} {t('governance.against')}
                  </span>
                </div>
              </div>
            )}

            <div className="flex justify-between items-center">
              <span className="text-sm text-secondary-500">
                Deadline: {selectedProposal.deadline}
              </span>
              {(selectedProposal.status === 'active' || selectedProposal.status === 'voting') && (
                <div className="flex gap-3">
                  <button
                    onClick={() => handleVote(selectedProposal.id, true)}
                    className="btn bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 hover:bg-green-200 dark:hover:bg-green-900/50 flex items-center gap-2"
                  >
                    <ThumbsUp size={18} />
                    {t('governance.voteFor')}
                  </button>
                  <button
                    onClick={() => handleVote(selectedProposal.id, false)}
                    className="btn bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50 flex items-center gap-2"
                  >
                    <ThumbsDown size={18} />
                    {t('governance.voteAgainst')}
                  </button>
                </div>
              )}
            </div>

            <button
              onClick={() => setSelectedProposal(null)}
              aria-label="Close dialog"
              className="absolute top-4 right-4 p-2 rounded-lg hover:bg-secondary-100 dark:hover:bg-secondary-700"
            >
              <XCircle size={20} className="text-secondary-400 dark:text-secondary-500" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
