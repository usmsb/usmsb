import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  RefreshCw,
  Loader2,
  AlertCircle,
  Filter,
} from 'lucide-react'
import { getWalletBalance, getTransactions } from '@/lib/api'
import type { TransactionRecord, WalletBalance as WalletBalanceType, StakeTier } from '@/types'
import clsx from 'clsx'
import { useAppStore } from '@/store'

interface WalletBalanceProps {
  onUpdate?: () => void
}

export function WalletBalanceCard({ onUpdate }: WalletBalanceProps) {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const [balance, setBalance] = useState<WalletBalanceType | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadBalance()
  }, [])

  const loadBalance = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getWalletBalance()
      setBalance({
        ...response,
        stake_tier: response.stake_tier as StakeTier,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load wallet balance')
    } finally {
      setIsLoading(false)
    }
  }

  const formatNumber = (num: number) => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  if (isLoading) {
    return (
      <div className={clsx(
        'card',
        isDark && 'border-neon-blue/20'
      )}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className={clsx(
            'w-5 h-5 animate-spin',
            isDark ? 'text-neon-blue' : 'text-blue-500'
          )} />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className={clsx(
        'card',
        isDark
          ? 'border-red-500/30 bg-red-900/10'
          : 'border-red-200 bg-red-50'
      )}>
        <div className="flex items-center gap-2">
          <AlertCircle size={20} className={isDark ? 'text-red-400' : 'text-red-500'} />
          <span className={isDark ? 'text-red-400' : 'text-red-700'}>{error}</span>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-blue/50'
    )}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Wallet size={20} className={isDark ? 'text-neon-blue' : 'text-blue-500'} />
          <h3 className={clsx(
            'text-lg font-semibold',
            'text-light-text-primary',
            isDark && 'text-neon-blue font-cyber'
          )}>{t('wallet.title', '钱包')}</h3>
        </div>
        <button
          onClick={loadBalance}
          className={clsx(
            'p-2 rounded-lg transition-colors',
            isDark
              ? 'hover:bg-neon-blue/10 text-gray-400 hover:text-neon-blue'
              : 'hover:bg-blue-50 text-gray-500 hover:text-blue-600'
          )}
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Total Assets */}
      <div className="text-center py-4">
        <p className={clsx(
          'text-sm',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>{t('wallet.totalAssets', '总资产')}</p>
        <p className={clsx(
          'text-3xl font-bold mt-1',
          isDark ? 'text-white' : 'text-gray-900'
        )}>
          {formatNumber(balance?.total_assets || 0)} VIBE
        </p>
      </div>

      {/* Balance Breakdown */}
      <div className="grid grid-cols-2 gap-3">
        <div className={clsx(
          'rounded-lg p-3',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <div className={clsx(
            'flex items-center gap-1 text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>
            <Wallet className="w-3 h-3" />
            <span>{t('wallet.balance', '余额')}</span>
          </div>
          <p className={clsx(
            'text-lg font-semibold mt-1',
            isDark ? 'text-white' : 'text-gray-900'
          )}>
            {formatNumber(balance?.balance || 0)}
          </p>
        </div>
        <div className={clsx(
          'rounded-lg p-3',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <div className={clsx(
            'flex items-center gap-1 text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>
            <TrendingUp className="w-3 h-3" />
            <span>{t('wallet.staked', '已质押')}</span>
          </div>
          <p className={clsx(
            'text-lg font-semibold mt-1',
            isDark ? 'text-white' : 'text-gray-900'
          )}>
            {formatNumber(balance?.staked_amount || 0)}
          </p>
        </div>
        <div className={clsx(
          'rounded-lg p-3',
          isDark ? 'bg-cyber-dark/50 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
        )}>
          <div className={clsx(
            'flex items-center gap-1 text-sm',
            isDark ? 'text-gray-400' : 'text-gray-500'
          )}>
            <TrendingDown className="w-3 h-3" />
            <span>{t('wallet.locked', '锁定')}</span>
          </div>
          <p className={clsx(
            'text-lg font-semibold mt-1',
            isDark ? 'text-white' : 'text-gray-900'
          )}>
            {formatNumber(balance?.locked_amount || 0)}
          </p>
        </div>
        <div className={clsx(
          'rounded-lg p-3',
          isDark ? 'bg-cyber-dark/50 border border-neon-green/20' : 'bg-green-50 border border-green-100'
        )}>
          <div className={clsx(
            'flex items-center gap-1 text-sm',
            isDark ? 'text-neon-green' : 'text-green-600'
          )}>
            <ArrowUpRight className="w-3 h-3" />
            <span>{t('wallet.rewards', '奖励')}</span>
          </div>
          <p className={clsx(
            'text-lg font-semibold mt-1',
            isDark ? 'text-neon-green' : 'text-green-600'
          )}>
            {formatNumber(balance?.pending_rewards || 0)}
          </p>
        </div>
      </div>

      {/* Tier Badge */}
      <div className={clsx(
        'flex items-center justify-between rounded-lg px-4 py-2 mt-4',
        isDark ? 'bg-cyber-dark/30 border border-gray-700/50' : 'bg-gray-50 border border-gray-100'
      )}>
        <span className={clsx(
          'text-sm',
          isDark ? 'text-gray-400' : 'text-gray-500'
        )}>{t('wallet.tier', '质押等级')}</span>
        <span className={clsx(
          'font-medium',
          isDark ? 'text-neon-blue' : 'text-blue-600'
        )}>{balance?.stake_tier || 'NONE'}</span>
      </div>
    </div>
  )
}

interface TransactionListProps {
  limit?: number
}

export function TransactionList({ limit = 10 }: TransactionListProps) {
  const { t } = useTranslation()
  const { theme } = useAppStore()
  const isDark = theme === 'dark'

  const [transactions, setTransactions] = useState<TransactionRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    loadTransactions()
  }, [filter])

  const loadTransactions = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await getTransactions(filter === 'all' ? undefined : filter, limit)
      setTransactions(response.transactions || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transactions')
    } finally {
      setIsLoading(false)
    }
  }

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const getTransactionIcon = (type: string) => {
    switch (type) {
      case 'deposit':
        return <ArrowDownRight className="w-4 h-4" />
      case 'withdraw':
        return <ArrowUpRight className="w-4 h-4" />
      case 'reward':
        return <TrendingUp className="w-4 h-4" />
      case 'payment':
        return <Wallet className="w-4 h-4" />
      default:
        return <Clock className="w-4 h-4" />
    }
  }

  const getStatusColor = (status: string, isDark: boolean) => {
    switch (status) {
      case 'completed':
        return isDark ? 'text-neon-green' : 'text-green-600'
      case 'pending':
        return isDark ? 'text-yellow-400' : 'text-yellow-600'
      case 'failed':
        return isDark ? 'text-red-400' : 'text-red-600'
      default:
        return isDark ? 'text-gray-400' : 'text-gray-500'
    }
  }

  const getAmountColor = (type: string, isDark: boolean) => {
    const isPositive = type === 'deposit' || type === 'reward'
    return isPositive
      ? (isDark ? 'text-neon-green' : 'text-green-600')
      : (isDark ? 'text-red-400' : 'text-red-600')
  }

  if (isLoading) {
    return (
      <div className={clsx(
        'card',
        isDark && 'border-neon-blue/20'
      )}>
        <div className="flex items-center justify-center py-8">
          <Loader2 className={clsx(
            'w-5 h-5 animate-spin',
            isDark ? 'text-neon-blue' : 'text-blue-500'
          )} />
        </div>
      </div>
    )
  }

  return (
    <div className={clsx(
      'card',
      isDark && 'hover:border-neon-blue/50'
    )}>
      <div className="flex items-center justify-between mb-4">
        <h3 className={clsx(
          'text-lg font-semibold',
          'text-light-text-primary',
          isDark && 'text-neon-blue font-cyber'
        )}>{t('wallet.transactions', '交易记录')}</h3>
        <div className="flex items-center gap-2">
          <Filter size={16} className={isDark ? 'text-gray-400' : 'text-gray-500'} />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className={clsx(
              'rounded-lg px-2 py-1 text-sm focus:outline-none',
              isDark
                ? 'bg-cyber-dark border border-gray-700 text-white focus:border-neon-blue'
                : 'bg-white border border-gray-200 text-gray-900 focus:border-blue-500'
            )}
          >
            <option value="all">{t('wallet.allTypes', '全部')}</option>
            <option value="deposit">{t('wallet.deposits', '充值')}</option>
            <option value="withdraw">{t('wallet.withdrawals', '提现')}</option>
            <option value="reward">{t('wallet.rewards', '奖励')}</option>
            <option value="payment">{t('wallet.payments', '支付')}</option>
          </select>
        </div>
      </div>

      {error && (
        <div className={clsx(
          'flex items-center gap-2 text-sm mb-4',
          isDark ? 'text-red-400' : 'text-red-600'
        )}>
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {transactions.length === 0 ? (
        <div className={clsx(
          'text-center py-8',
          isDark ? 'text-gray-500' : 'text-gray-400'
        )}>
          {t('wallet.noTransactions', '暂无交易记录')}
        </div>
      ) : (
        <div className="space-y-2">
          {transactions.map((tx) => (
            <div
              key={tx.id}
              className={clsx(
                'flex items-center justify-between p-3 rounded-lg transition-colors',
                isDark
                  ? 'bg-cyber-dark/30 hover:bg-cyber-dark/50 border border-gray-800'
                  : 'bg-gray-50 hover:bg-gray-100 border border-gray-100'
              )}
            >
              <div className="flex items-center gap-3">
                <div className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  isDark ? 'bg-gray-800' : 'bg-white'
                )}>
                  <span className={getAmountColor(tx.transaction_type, isDark)}>
                    {getTransactionIcon(tx.transaction_type)}
                  </span>
                </div>
                <div>
                  <p className={clsx(
                    'font-medium text-sm',
                    isDark ? 'text-white' : 'text-gray-900'
                  )}>
                    {tx.title || t(`wallet.txType.${tx.transaction_type}`, tx.transaction_type)}
                  </p>
                  <p className={clsx(
                    'text-xs',
                    isDark ? 'text-gray-500' : 'text-gray-400'
                  )}>{formatDate(tx.created_at)}</p>
                </div>
              </div>
              <div className="text-right">
                <p className={clsx(
                  'font-medium',
                  getAmountColor(tx.transaction_type, isDark)
                )}>
                  {tx.transaction_type === 'deposit' || tx.transaction_type === 'reward' ? '+' : '-'}
                  {tx.amount.toLocaleString()} VIBE
                </p>
                <p className={clsx(
                  'text-xs',
                  getStatusColor(tx.status, isDark)
                )}>{t(`wallet.status.${tx.status}`, tx.status)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default WalletBalanceCard
