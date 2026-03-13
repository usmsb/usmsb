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

interface WalletBalanceProps {
  onUpdate?: () => void
}

export function WalletBalanceCard({ onUpdate }: WalletBalanceProps) {
  const { t } = useTranslation()
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

  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wallet className="w-5 h-5 text-neon-blue" />
          <h3 className="text-lg font-semibold text-white">{t('wallet.title', 'Wallet')}</h3>
        </div>
        <button
          onClick={loadBalance}
          className="p-2 hover:bg-gray-700 rounded-lg transition-colors text-gray-400 hover:text-white"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Total Assets */}
      <div className="text-center py-4">
        <p className="text-sm text-gray-400">{t('wallet.totalAssets', 'Total Assets')}</p>
        <p className="text-3xl font-bold text-white mt-1">
          {formatNumber(balance?.total_assets || 0)} VIBE
        </p>
      </div>

      {/* Balance Breakdown */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-gray-400 text-sm">
            <Wallet className="w-3 h-3" />
            <span>{t('wallet.balance', 'Balance')}</span>
          </div>
          <p className="text-lg font-semibold text-white mt-1">
            {formatNumber(balance?.balance || 0)}
          </p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-gray-400 text-sm">
            <TrendingUp className="w-3 h-3" />
            <span>{t('wallet.staked', 'Staked')}</span>
          </div>
          <p className="text-lg font-semibold text-white mt-1">
            {formatNumber(balance?.staked_amount || 0)}
          </p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-gray-400 text-sm">
            <TrendingDown className="w-3 h-3" />
            <span>{t('wallet.locked', 'Locked')}</span>
          </div>
          <p className="text-lg font-semibold text-white mt-1">
            {formatNumber(balance?.locked_amount || 0)}
          </p>
        </div>
        <div className="bg-gray-700/50 rounded-lg p-3">
          <div className="flex items-center gap-1 text-neon-green text-sm">
            <ArrowUpRight className="w-3 h-3" />
            <span>{t('wallet.rewards', 'Rewards')}</span>
          </div>
          <p className="text-lg font-semibold text-neon-green mt-1">
            {formatNumber(balance?.pending_rewards || 0)}
          </p>
        </div>
      </div>

      {/* Tier Badge */}
      <div className="flex items-center justify-between bg-gray-700/30 rounded-lg px-4 py-2">
        <span className="text-sm text-gray-400">{t('wallet.tier', 'Stake Tier')}</span>
        <span className="font-medium text-neon-blue">{balance?.stake_tier || 'NONE'}</span>
      </div>
    </div>
  )
}

interface TransactionListProps {
  limit?: number
}

export function TransactionList({ limit = 10 }: TransactionListProps) {
  const { t } = useTranslation()
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
        return <ArrowDownRight className="w-4 h-4 text-green-400" />
      case 'withdraw':
        return <ArrowUpRight className="w-4 h-4 text-red-400" />
      case 'reward':
        return <TrendingUp className="w-4 h-4 text-neon-green" />
      case 'payment':
        return <Wallet className="w-4 h-4 text-blue-400" />
      default:
        return <Clock className="w-4 h-4 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-400'
      case 'pending':
        return 'text-yellow-400'
      case 'failed':
        return 'text-red-400'
      default:
        return 'text-gray-400'
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

  return (
    <div className="bg-gray-800/50 rounded-xl border border-gray-700 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">{t('wallet.transactions', 'Transactions')}</h3>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-1 text-sm text-white focus:outline-none"
          >
            <option value="all">{t('wallet.allTypes', 'All')}</option>
            <option value="deposit">{t('wallet.deposits', 'Deposits')}</option>
            <option value="withdraw">{t('wallet.withdrawals', 'Withdrawals')}</option>
            <option value="reward">{t('wallet.rewards', 'Rewards')}</option>
            <option value="payment">{t('wallet.payments', 'Payments')}</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-400 text-sm">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {transactions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          {t('wallet.noTransactions', 'No transactions yet')}
        </div>
      ) : (
        <div className="space-y-2">
          {transactions.map((tx) => (
            <div
              key={tx.id}
              className="flex items-center justify-between p-3 bg-gray-700/30 rounded-lg hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                  {getTransactionIcon(tx.transaction_type)}
                </div>
                <div>
                  <p className="font-medium text-white text-sm">
                    {tx.title || tx.transaction_type}
                  </p>
                  <p className="text-xs text-gray-500">{formatDate(tx.created_at)}</p>
                </div>
              </div>
              <div className="text-right">
                <p
                  className={clsx(
                    'font-medium',
                    tx.transaction_type === 'deposit' || tx.transaction_type === 'reward'
                      ? 'text-green-400'
                      : 'text-red-400'
                  )}
                >
                  {tx.transaction_type === 'deposit' || tx.transaction_type === 'reward' ? '+' : '-'}
                  {tx.amount.toLocaleString()} VIBE
                </p>
                <p className={clsx('text-xs', getStatusColor(tx.status))}>{tx.status}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default WalletBalanceCard
