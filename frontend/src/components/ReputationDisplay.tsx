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
import { useAppStore } from '@/store'

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
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

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
        return <TrendingUp className="w-4 h-4" />
      case 'transaction_fail':
        return <TrendingUp className="w-4 h-4 rotate-180" />
      case 'positive_review':
        return <Star className="w-4 h-4" />
      case 'negative_review':
        return <Star className="w-4 h-4" />
      case 'stake_bonus':
        return <Award className="w-4 h-4" />
      default:
        return <Award className="w-4 h-4" />
    }
  }

  const getEventColor = (eventType: string, isPositive: boolean) => {
    if (!isPositive) {
      return isDark ? 'text-red-400' : 'text-red-600'
    }
    switch (eventType) {
      case 'transaction_success':
        return isDark ? 'text-neon-green' : 'text-green-600'
      case 'positive_review':
        return isDark ? 'text-yellow-400' : 'text-yellow-600'
      case 'stake_bonus':
        return isDark ? 'text-neon-blue' : 'text-blue-600'
      default:
        return isDark ? 'text-gray-400' : 'text-gray-600'
    }
  }

  if (isLoading) {
    return (
      <div className={clsx(
        'card',
        isDark && 'border-neon-purple/20'
      )}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className={clsx(
            'w-5 h-5 animate-spin',
            isDark ? 'text-neon-purple' : 'text-purple-500'
          )} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={clsx(
        'card',
        isDark ? 'border-red-500/30 bg-red-900/10' : 'border-red-200 bg-red-50'
      )}>
        <div className="flex items-center gap-2">
          <AlertCircle size={20} className={isDark ? 'text-red-400' : 'text-red-500'} />
          <span className={isDark ? 'text-red-400' : 'text-red-700'}>{error}</span>
        </div>
      </div>
    )
  }

  const currentTier = getTierInfo()
  const nextTier = getNextTier()

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-purple/50'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Star size={20} className={isDark ? 'text-yellow-400' : 'text-yellow-500'} />
          <h3 className={clsx(
            'text-lg font-semibold',
            'text-light-text-primary',
            isDark && 'text-neon-purple font-cyber'
          )}>{t('reputation.title', '信誉')}</h3>
        </div>
        <button
          onClick={loadReputation}
          className={clsx(
            'p-2 rounded-lg transition-colors',
            isDark
              ? 'hover:bg-neon-purple/10 text-gray-400 hover:text-neon-purple'
              : 'hover:bg-purple-50 text-gray-500 hover:text-purple-600'
          )}
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
        <p className={clsx(
          'text-4xl font-bold',
          isDark ? 'text-white' : 'text-gray-900'
        )}>{reputation?.score || 0}</p>
        <p className={clsx(
          'text-sm mt-1',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>{t('reputation.score', '信誉分数')}</p>
      </div>

      {/* Progress to Next Tier */}
      {nextTier && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className={isDark ? 'text-gray-400' : 'text-gray-500'}>
              {t('reputation.progressTo', '进度: {{tier}}', { tier: nextTier.name })}
            </span>
            <span style={{ color: nextTier.color }}>{nextTier.name}</span>
          </div>
          <div className={clsx(
            'h-2 rounded-full overflow-hidden',
            isDark ? 'bg-gray-800' : 'bg-gray-200'
          )}>
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
          <p className={clsx(
            'text-xs',
            isDark ? 'text-gray-500' : 'text-gray-400'
          )}>
            {t('reputation.needed', '{{amount}} 积分至 {{tier}}', {
              amount: nextTier.min - (reputation?.score || 0),
              tier: nextTier.name,
            })}
          </p>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-3 mt-4">
        <div className={clsx(
          'rounded-lg p-3 text-center',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <p className={clsx(
            'text-2xl font-bold',
            isDark ? 'text-white' : 'text-gray-900'
          )}>{reputation?.total_transactions || 0}</p>
          <p className={clsx(
            'text-xs',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>{t('reputation.totalTx', '总交易')}</p>
        </div>
        <div className={clsx(
          'rounded-lg p-3 text-center',
          isDark ? 'bg-cyber-dark/50 border border-neon-green/20' : 'bg-green-50 border border-green-100'
        )}>
          <p className={clsx(
            'text-2xl font-bold',
            isDark ? 'text-neon-green' : 'text-green-600'
          )}>{reputation?.success_rate || 0}%</p>
          <p className={clsx(
            'text-xs',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>{t('reputation.successRate', '成功率')}</p>
        </div>
        <div className={clsx(
          'rounded-lg p-3 text-center',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <p className={clsx(
            'text-2xl font-bold flex items-center justify-center gap-1',
            isDark ? 'text-yellow-400' : 'text-yellow-500'
          )}>
            <Star className="w-4 h-4 fill-current" />
            {reputation?.avg_rating?.toFixed(1) || '0.0'}
          </p>
          <p className={clsx(
            'text-xs',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>{t('reputation.avgRating', '平均评分')}</p>
        </div>
        <div className={clsx(
          'rounded-lg p-3 text-center',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <p className={clsx(
            'text-2xl font-bold',
            isDark ? 'text-white' : 'text-gray-900'
          )}>{reputation?.total_ratings || 0}</p>
          <p className={clsx(
            'text-xs',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>{t('reputation.totalRatings', '总评分')}</p>
        </div>
      </div>

      {/* History Toggle */}
      {showHistory && history.length > 0 && (
        <div className="mt-4">
          <button
            onClick={() => setShowHistoryPanel(!showHistoryPanel)}
            className={clsx(
              'w-full flex items-center justify-between p-3 rounded-lg transition-colors',
              isDark
                ? 'bg-cyber-dark/30 hover:bg-cyber-dark/50 border border-gray-800'
                : 'bg-gray-50 hover:bg-gray-100 border border-gray-100'
            )}
          >
            <div className={clsx(
              'flex items-center gap-2',
              isDark ? 'text-gray-400' : 'text-gray-500'
            )}>
              <History className="w-4 h-4" />
              <span>{t('reputation.history', '最近活动')}</span>
            </div>
            <ChevronRight
              className={clsx(
                'w-4 h-4 transition-transform',
                isDark ? 'text-gray-400' : 'text-gray-500',
                showHistoryPanel && 'rotate-90'
              )}
            />
          </button>

          {showHistoryPanel && (
            <div className="mt-2 space-y-2">
              {history.slice(0, 5).map((event, index) => (
                <div
                  key={index}
                  className={clsx(
                    'flex items-center justify-between p-3 rounded-lg',
                    isDark ? 'bg-cyber-dark/30 border border-gray-800' : 'bg-gray-50 border border-gray-100'
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center',
                      isDark ? 'bg-gray-800' : 'bg-white'
                    )}>
                      <span className={getEventColor(event.event_type, event.change > 0)}>
                        {getEventIcon(event.event_type)}
                      </span>
                    </div>
                    <div>
                      <p className={clsx(
                        'text-sm',
                        isDark ? 'text-white' : 'text-gray-900'
                      )}>{event.reason}</p>
                      <div className={clsx(
                        'flex items-center gap-1 text-xs',
                        isDark ? 'text-gray-500' : 'text-gray-400'
                      )}>
                        <Clock className="w-3 h-3" />
                        <span>{formatDate(event.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                  <span
                    className={clsx(
                      'font-medium',
                      event.change > 0
                        ? (isDark ? 'text-neon-green' : 'text-green-600')
                        : (isDark ? 'text-red-400' : 'text-red-600')
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
      <div className="space-y-2 mt-4">
        <p className={clsx(
          'text-sm font-medium',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>{t('reputation.tiers', '信誉等级')}</p>
        <div className="flex flex-wrap gap-2">
          {REPUTATION_TIERS.map((tier) => {
            const isCurrent = reputation?.tier?.toLowerCase() === tier.name.toLowerCase()
            const isAchieved = reputation && reputation.score >= tier.min
            return (
              <div
                key={tier.name}
                className={clsx(
                  'px-3 py-1 rounded-full text-xs font-medium transition-all',
                  isCurrent ? 'ring-2' : '',
                  isAchieved ? 'opacity-100' : 'opacity-40'
                )}
                style={{
                  backgroundColor: `${tier.color}20`,
                  color: tier.color,
                  ...(isCurrent && isDark ? { boxShadow: `0 0 10px ${tier.color}50` } : {}),
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
