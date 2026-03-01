import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Star,
  TrendingUp,
  Award,
  RefreshCw,
  Loader2,
  AlertCircle,
  ChevronRight,
  Clock,
  History,
} from 'lucide-react'
import { getReputation, getReputationHistory } from '@/lib/api'
import clsx from 'clsx'

interface ReputationDisplayProps {
  showHistory?: boolean
}

const REPUTATION_TIERS = [
  { name: 'Newcomer', min: 0, max: 99, color: '#808080' },
  { name: 'Bronze', min: 100, max: 299, color: '#cd7f32' },
  { name: 'Silver', min: 300, max: 599, color: '#c0c0c0' },
  { name: 'Gold', min: 600, max: 999, color: '#ffd700' },
  { name: 'Platinum', min: 1000, max: Infinity, color: '#e5e4e2' },
]

export function ReputationDisplay({ showHistory = false }: ReputationDisplayProps) {
  const { t } = useTranslation()
  const [reputation, setReputation] = useState<{
    score: number
    tier: string
    total_transactions: number
    successful_transactions: number
    success_rate: number
    avg_rating: number
    total_ratings: number
  } | null>(null)
  const [history, setHistory] = useState<Array<{
    timestamp: number
    event_type: string
    change: number
    reason: string
  }>>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showHistoryPanel, setShowHistoryPanel] = useState(false)

  useEffect(() => {
    loadReputation()
  }, [])

  const loadReputation = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [reputationResponse, historyResponse] = await Promise.all([
        getReputation(),
        showHistory ? getReputationHistory(10) : Promise.resolve({ history: [] }),
      ])
      setReputation(reputationResponse)
      setHistory(historyResponse.history || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load reputation')
    } finally {
      setIsLoading(false)
    }
  }

  const getTierInfo = () => {
    if (!reputation) return REPUTATION_TIERS[0]
    return REPUTATION_TIERS.find(
      (t) => reputation.score >= t.min && reputation.score <= t.max
    ) || REPUTATION_TIERS[0]
  }

  const getNextTier = () => {
    if (!reputation) return REPUTATION_TIERS[1]
    const currentIndex = REPUTATION_TIERS.findIndex(
      (t) => reputation.score >= t.min && reputation.score <= t.max
    )
    return currentIndex < REPUTATION_TIERS.length - 1
      ? REPUTATION_TIERS[currentIndex + 1]
      : null
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
    })
  }

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'transaction_success':
        return <TrendingUp className="w-4 h-4 text-green-400" />
      case 'transaction_fail':
        return <TrendingUp className="w-4 h-4 text-red-400 rotate-180" />
      case 'positive_review':
        return <Star className="w-4 h-4 text-yellow-400" />
      case 'negative_review':
        return <Star className="w-4 h-4 text-gray-400" />
      case 'stake_bonus':
        return <Award className="w-4 h-4 text-neon-blue" />
      default:
        return <Award className="w-4 h-4 text-gray-400" />
    }
  }

  if (isLoading) {
    return (
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
        <div className="flex items-center justify-center py-4">
          <Loader2 className="w-5 h-5 animate-spin text-neon-blue" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6">
        <div className="flex items-center gap-2 text-red-400">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      </div>
    )
  }

  const currentTier = getTierInfo()
  const nextTier = getNextTier()

  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Star className="w-5 h-5 text-yellow-400" />
          <h3 className="text-lg font-semibold text-white">{t('reputation.title', 'Reputation')}</h3>
        </div>
        <button
          onClick={loadReputation}
          className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Score Display */}
      <div className="text-center py-4">
        <div className="flex items-center justify-center gap-2 mb-2">
          <span
            className="px-3 py-1 rounded-full text-sm font-medium"
            style={{
              backgroundColor: `${currentTier.color}20`,
              color: currentTier.color,
            }}
          >
            {currentTier.name}
          </span>
        </div>
        <p className="text-4xl font-bold text-white">{reputation?.score || 0}</p>
        <p className="text-sm text-gray-400 mt-1">{t('reputation.score', 'Reputation Score')}</p>
      </div>

      {/* Progress to Next Tier */}
      {nextTier && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400">{t('reputation.progressTo', 'Progress to {{tier}}', { tier: nextTier.name })}</span>
            <span style={{ color: nextTier.color }}>{nextTier.name}</span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(
                  100,
                  (((reputation?.score || 0) - currentTier.min) / (nextTier.min - currentTier.min)) * 100
                )}%`,
                backgroundColor: currentTier.color,
              }}
            />
          </div>
          <p className="text-xs text-gray-500">
            {t('reputation.needed', '{{amount}} points to {{tier}}', {
              amount: nextTier.min - (reputation?.score || 0),
              tier: nextTier.name,
            })}
          </p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-white">{reputation?.total_transactions || 0}</p>
          <p className="text-xs text-gray-400">{t('reputation.totalTx', 'Total Transactions')}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-green-400">{reputation?.success_rate || 0}%</p>
          <p className="text-xs text-gray-400">{t('reputation.successRate', 'Success Rate')}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-yellow-400 flex items-center justify-center gap-1">
            <Star className="w-4 h-4 fill-current" />
            {reputation?.avg_rating?.toFixed(1) || '0.0'}
          </p>
          <p className="text-xs text-gray-400">{t('reputation.avgRating', 'Avg Rating')}</p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3 text-center">
          <p className="text-2xl font-bold text-white">{reputation?.total_ratings || 0}</p>
          <p className="text-xs text-gray-400">{t('reputation.totalRatings', 'Total Ratings')}</p>
        </div>
      </div>

      {/* History Toggle */}
      {showHistory && history.length > 0 && (
        <div>
          <button
            onClick={() => setShowHistoryPanel(!showHistoryPanel)}
            className="w-full flex items-center justify-between p-3 bg-gray-700/30 rounded-lg hover:bg-gray-700/50 transition-colors"
          >
            <div className="flex items-center gap-2 text-gray-400">
              <History className="w-4 h-4" />
              <span>{t('reputation.history', 'Recent Activity')}</span>
            </div>
            <ChevronRight
              className={clsx(
                'w-4 h-4 text-gray-400 transition-transform',
                showHistoryPanel && 'rotate-90'
              )}
            />
          </button>

          {showHistoryPanel && (
            <div className="mt-2 space-y-2">
              {history.slice(0, 5).map((event, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-700/20 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                      {getEventIcon(event.event_type)}
                    </div>
                    <div>
                      <p className="text-sm text-white">{event.reason}</p>
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(event.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                  <span
                    className={clsx(
                      'font-medium',
                      event.change > 0 ? 'text-green-400' : 'text-red-400'
                    )}
                  >
                    {event.change > 0 ? '+' : ''}{event.change}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tier Badges */}
      <div className="space-y-2">
        <p className="text-sm font-medium text-gray-400">{t('reputation.tiers', 'Reputation Tiers')}</p>
        <div className="flex flex-wrap gap-2">
          {REPUTATION_TIERS.map((tier) => {
            const isCurrent = reputation?.tier?.toLowerCase() === tier.name.toLowerCase()
            const isAchieved = reputation && reputation.score >= tier.min
            return (
              <div
                key={tier.name}
                className={clsx(
                  'px-3 py-1 rounded-full text-xs font-medium transition-all',
                  isCurrent
                    ? 'ring-2 ring-offset-2 ring-offset-gray-800'
                    : '',
                  isAchieved ? 'opacity-100' : 'opacity-40'
                )}
                style={{
                  backgroundColor: `${tier.color}20`,
                  color: tier.color,
                }}
              >
                {tier.name}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default ReputationDisplay
