import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Coins,
  TrendingUp,
  Lock,
  Unlock,
  AlertCircle,
  Loader2,
  Gift,
  ArrowUpRight,
  ArrowDownRight,
  Info,
} from 'lucide-react'
import {
  getStakingInfo,
  depositStake,
  withdrawStake,
  getStakingRewards,
  claimRewards,
} from '@/lib/api'
import clsx from 'clsx'

interface StakingPanelProps {
  onStakeChange?: () => void
}

const STAKE_TIERS = [
  { tier: 'BRONZE', min: 100, max: 999, label: 'Bronze', agents: 1, discount: '0%', color: '#cd7f32' },
  { tier: 'SILVER', min: 1000, max: 4999, label: 'Silver', agents: 3, discount: '5%', color: '#c0c0c0' },
  { tier: 'GOLD', min: 5000, max: 9999, label: 'Gold', agents: 10, discount: '10%', color: '#ffd700' },
  { tier: 'PLATINUM', min: 10000, max: Infinity, label: 'Platinum', agents: 50, discount: '20%', color: '#e5e4e2' },
]

export function StakingPanel({ onStakeChange }: StakingPanelProps) {
  const { t } = useTranslation()
  const [stakeInfo, setStakeInfo] = useState<{
    staked_amount: number
    stake_status: string
    stake_tier: string
    locked_stake: number
    pending_rewards: number
    apy: number
    tier_benefits?: { max_agents: number; discount: number }
  } | null>(null)
  const [rewardsInfo, setRewardsInfo] = useState<{
    pending_rewards: number
    total_claimed: number
    apy: number
  } | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionType, setActionType] = useState<'deposit' | 'withdraw' | 'claim' | null>(null)
  const [showDepositModal, setShowDepositModal] = useState(false)
  const [showWithdrawModal, setShowWithdrawModal] = useState(false)
  const [amount, setAmount] = useState('')

  useEffect(() => {
    loadStakingInfo()
  }, [])

  const loadStakingInfo = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [stakeResponse, rewardsResponse] = await Promise.all([
        getStakingInfo(),
        getStakingRewards(),
      ])
      setStakeInfo(stakeResponse)
      setRewardsInfo(rewardsResponse)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load staking info')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeposit = async () => {
    const depositAmount = parseFloat(amount)
    if (isNaN(depositAmount) || depositAmount <= 0) {
      setError('Please enter a valid amount')
      return
    }

    setActionType('deposit')
    setError(null)
    try {
      const response = await depositStake(depositAmount)
      setStakeInfo({
        staked_amount: response.staked_amount,
        stake_status: response.stake_status,
        stake_tier: response.stake_tier,
        locked_stake: response.locked_stake,
        pending_rewards: response.pending_rewards,
        apy: response.apy,
        tier_benefits: response.tier_benefits,
      })
      setShowDepositModal(false)
      setAmount('')
      onStakeChange?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to deposit stake')
    } finally {
      setActionType(null)
    }
  }

  const handleWithdraw = async () => {
    const withdrawAmount = parseFloat(amount)
    if (isNaN(withdrawAmount) || withdrawAmount <= 0) {
      setError('Please enter a valid amount')
      return
    }

    setActionType('withdraw')
    setError(null)
    try {
      const response = await withdrawStake(withdrawAmount)
      setStakeInfo({
        staked_amount: response.staked_amount,
        stake_status: response.stake_status,
        stake_tier: response.stake_tier,
        locked_stake: 0,
        pending_rewards: response.pending_rewards,
        apy: response.apy,
        tier_benefits: response.tier_benefits,
      })
      setShowWithdrawModal(false)
      setAmount('')
      onStakeChange?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to withdraw stake')
    } finally {
      setActionType(null)
    }
  }

  const handleClaimRewards = async () => {
    setActionType('claim')
    setError(null)
    try {
      await claimRewards()
      await loadStakingInfo()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to claim rewards')
    } finally {
      setActionType(null)
    }
  }

  const getCurrentTier = () => {
    if (!stakeInfo) return STAKE_TIERS[0]
    return STAKE_TIERS.find(
      (t) => stakeInfo.staked_amount >= t.min && stakeInfo.staked_amount <= t.max
    ) || STAKE_TIERS[0]
  }

  const getNextTier = () => {
    if (!stakeInfo) return STAKE_TIERS[1]
    const currentIndex = STAKE_TIERS.findIndex(
      (t) => stakeInfo.staked_amount >= t.min && stakeInfo.staked_amount <= t.max
    )
    return currentIndex < STAKE_TIERS.length - 1 ? STAKE_TIERS[currentIndex + 1] : null
  }

  const formatNumber = (num: number) => {
    return num.toLocaleString(undefined, { maximumFractionDigits: 2 })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-neon-blue" />
        <span className="ml-2 text-gray-400">{t('common.loading', 'Loading...')}</span>
      </div>
    )
  }

  const currentTier = getCurrentTier()
  const nextTier = getNextTier()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Coins className="w-5 h-5 text-neon-blue" />
          <h3 className="text-lg font-semibold text-white">{t('staking.title', 'Staking')}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">{t('staking.apy', 'APY')}:</span>
          <span className="text-neon-green font-medium">{stakeInfo?.apy || 0}%</span>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/30 border border-red-500/50 rounded-lg flex items-center gap-2 text-red-400">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {/* Main Stats */}
      <div className="grid grid-cols-2 gap-4">
        {/* Staked Amount */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Lock className="w-4 h-4" />
            {t('staking.stakedAmount', 'Staked Amount')}
          </div>
          <div className="text-2xl font-bold text-white">
            {formatNumber(stakeInfo?.staked_amount || 0)} VIBE
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span
              className="px-2 py-0.5 text-xs font-medium rounded"
              style={{
                backgroundColor: `${currentTier.color}20`,
                color: currentTier.color,
              }}
            >
              {currentTier.label}
            </span>
          </div>
        </div>

        {/* Pending Rewards */}
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
          <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
            <Gift className="w-4 h-4" />
            {t('staking.pendingRewards', 'Pending Rewards')}
          </div>
          <div className="text-2xl font-bold text-neon-green">
            {formatNumber(stakeInfo?.pending_rewards || 0)} VIBE
          </div>
          <button
            onClick={handleClaimRewards}
            disabled={actionType === 'claim' || !stakeInfo?.pending_rewards}
            className={clsx(
              'mt-2 px-3 py-1 text-sm rounded-lg transition-all',
              'bg-neon-green/20 text-neon-green hover:bg-neon-green/30',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
          >
            {actionType === 'claim' ? (
              <span className="flex items-center gap-1">
                <Loader2 className="w-3 h-3 animate-spin" />
                {t('staking.claiming', 'Claiming...')}
              </span>
            ) : (
              t('staking.claimRewards', 'Claim Rewards')
            )}
          </button>
        </div>
      </div>

      {/* Tier Progress */}
      {nextTier && (
        <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">{t('staking.nextTier', 'Next Tier')}</span>
            <span className="text-sm font-medium" style={{ color: nextTier.color }}>
              {nextTier.label}
            </span>
          </div>
          <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(
                  100,
                  ((stakeInfo?.staked_amount || 0) / nextTier.min) * 100
                )}%`,
                backgroundColor: currentTier.color,
              }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-2">
            {t('staking.tierProgress', 'Stake {{amount}} more VIBE to reach {{tier}}', {
              amount: formatNumber(nextTier.min - (stakeInfo?.staked_amount || 0)),
              tier: nextTier.label,
            })}
          </p>
        </div>
      )}

      {/* Tier Benefits */}
      <div className="bg-gray-800/50 rounded-lg border border-gray-700 p-4">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-white">
            {t('staking.tierBenefits', 'Tier Benefits')}
          </span>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">{t('staking.maxAgents', 'Max Agents')}:</span>
            <span className="ml-2 text-white">{stakeInfo?.tier_benefits?.max_agents || 1}</span>
          </div>
          <div>
            <span className="text-gray-400">{t('staking.discount', 'Discount')}:</span>
            <span className="ml-2 text-neon-green">{stakeInfo?.tier_benefits?.discount || 0}%</span>
          </div>
        </div>
      </div>

      {/* All Tiers */}
      <div className="space-y-2">
        <span className="text-sm font-medium text-gray-400">{t('staking.allTiers', 'Staking Tiers')}</span>
        {STAKE_TIERS.map((tier) => {
          const isCurrent = stakeInfo?.stake_tier === tier.tier
          return (
            <div
              key={tier.tier}
              className={clsx(
                'p-3 rounded-lg border transition-all',
                isCurrent
                  ? 'bg-gray-800 border-gray-600'
                  : 'bg-gray-800/30 border-gray-700/50'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: tier.color }}
                  />
                  <span className="font-medium text-white">{tier.label}</span>
                  {isCurrent && (
                    <span className="px-2 py-0.5 text-xs bg-neon-blue/20 text-neon-blue rounded">
                      {t('staking.current', 'Current')}
                    </span>
                  )}
                </div>
                <span className="text-sm text-gray-400">
                  {tier.min.toLocaleString()} - {tier.max === Infinity ? '∞' : tier.max.toLocaleString()} VIBE
                </span>
              </div>
              <div className="flex items-center gap-4 mt-1 text-xs text-gray-500">
                <span>{tier.agents} agents</span>
                <span>{tier.discount} discount</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={() => setShowDepositModal(true)}
          className="flex-1 flex items-center justify-center gap-2 py-3 bg-neon-blue hover:bg-neon-blue/80 text-gray-900 rounded-lg font-medium transition-all"
        >
          <ArrowUpRight className="w-4 h-4" />
          {t('staking.deposit', 'Deposit')}
        </button>
        <button
          onClick={() => setShowWithdrawModal(true)}
          disabled={!stakeInfo?.staked_amount}
          className={clsx(
            'flex-1 flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-all',
            'bg-gray-700 hover:bg-gray-600 text-white',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
        >
          <ArrowDownRight className="w-4 h-4" />
          {t('staking.withdraw', 'Withdraw')}
        </button>
      </div>

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-white mb-4">
              {t('staking.depositTitle', 'Deposit VIBE')}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  {t('staking.amount', 'Amount')}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    min={100}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white text-xl placeholder-gray-500 focus:border-neon-blue focus:outline-none"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
                    VIBE
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {t('staking.minDeposit', 'Minimum deposit: 100 VIBE')}
                </p>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowDepositModal(false)}
                  className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-all"
                >
                  {t('common.cancel', 'Cancel')}
                </button>
                <button
                  onClick={handleDeposit}
                  disabled={actionType === 'deposit'}
                  className={clsx(
                    'flex-1 py-2 bg-neon-blue hover:bg-neon-blue/80 text-gray-900 rounded-lg font-medium transition-all',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {actionType === 'deposit' ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('staking.depositing', 'Depositing...')}
                    </span>
                  ) : (
                    t('staking.depositButton', 'Deposit')
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Withdraw Modal */}
      {showWithdrawModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md bg-gray-800 rounded-xl border border-gray-700 p-6 shadow-xl">
            <h3 className="text-lg font-semibold text-white mb-4">
              {t('staking.withdrawTitle', 'Withdraw VIBE')}
            </h3>
            <div className="space-y-4">
              <div className="p-3 bg-gray-700/50 rounded-lg">
                <div className="text-sm text-gray-400">{t('staking.available', 'Available')}</div>
                <div className="text-xl font-bold text-white">
                  {formatNumber((stakeInfo?.staked_amount || 0) - (stakeInfo?.locked_stake || 0))} VIBE
                </div>
                {stakeInfo?.locked_stake ? (
                  <div className="text-xs text-yellow-400 mt-1">
                    {formatNumber(stakeInfo.locked_stake)} VIBE {t('staking.locked', 'locked')}
                  </div>
                ) : null}
              </div>

              <div>
                <label className="block text-sm text-gray-400 mb-1">
                  {t('staking.amount', 'Amount')}
                </label>
                <div className="relative">
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="0.00"
                    min={0}
                    max={(stakeInfo?.staked_amount || 0) - (stakeInfo?.locked_stake || 0)}
                    className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white text-xl placeholder-gray-500 focus:border-neon-blue focus:outline-none"
                  />
                  <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">
                    VIBE
                  </span>
                </div>
                <button
                  onClick={() =>
                    setAmount(
                      String((stakeInfo?.staked_amount || 0) - (stakeInfo?.locked_stake || 0))
                    )
                  }
                  className="text-xs text-neon-blue hover:text-neon-blue/80 mt-1"
                >
                  {t('staking.withdrawAll', 'Withdraw all')}
                </button>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowWithdrawModal(false)}
                  className="flex-1 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-all"
                >
                  {t('common.cancel', 'Cancel')}
                </button>
                <button
                  onClick={handleWithdraw}
                  disabled={actionType === 'withdraw'}
                  className={clsx(
                    'flex-1 py-2 bg-neon-purple hover:bg-neon-purple/80 text-white rounded-lg font-medium transition-all',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {actionType === 'withdraw' ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('staking.withdrawing', 'Withdrawing...')}
                    </span>
                  ) : (
                    t('staking.withdrawButton', 'Withdraw')
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default StakingPanel
