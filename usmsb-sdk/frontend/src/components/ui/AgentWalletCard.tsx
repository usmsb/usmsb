import { useState } from 'react'
import { AgentWalletInfo } from '@/stores/authStore'
import { useAgentWallet } from '@/hooks/useAgentWallet'
import { Button } from './Button'
import { Input } from './Input'
import { useTranslation } from 'react-i18next'

interface AgentWalletCardProps {
  wallet: AgentWalletInfo
  onSelect?: (wallet: AgentWalletInfo) => void
  showActions?: boolean
}

export default function AgentWalletCard({
  wallet,
  onSelect,
  showActions = true,
}: AgentWalletCardProps) {
  const { t } = useTranslation()
  const {
    deposit,
    transfer,
    stake,
    unstake,
    updateLimits,
    removeWallet,
    canTransfer,
    isLoading,
  } = useAgentWallet()

  const [showDepositModal, setShowDepositModal] = useState(false)
  const [showTransferModal, setShowTransferModal] = useState(false)
  const [showStakeModal, setShowStakeModal] = useState(false)
  const [showLimitsModal, setShowLimitsModal] = useState(false)

  const [depositAmount, setDepositAmount] = useState('')
  const [transferTo, setTransferTo] = useState('')
  const [transferAmount, setTransferAmount] = useState('')
  const [stakeAmount, setStakeAmount] = useState('')
  const [maxPerTx, setMaxPerTx] = useState(String(wallet.maxPerTx || 1000))
  const [dailyLimit, setDailyLimit] = useState(String(wallet.dailyLimit || 10000))

  const handleDeposit = async () => {
    const amount = parseFloat(depositAmount)
    if (amount > 0) {
      await deposit(wallet.agentId, amount)
      setDepositAmount('')
      setShowDepositModal(false)
    }
  }

  const handleTransfer = async () => {
    const amount = parseFloat(transferAmount)
    if (canTransfer(wallet, amount) && transferTo) {
      const success = await transfer(wallet.agentId, transferTo, amount)
      if (success) {
        setTransferTo('')
        setTransferAmount('')
        setShowTransferModal(false)
      }
    }
  }

  const handleStake = async () => {
    const amount = parseFloat(stakeAmount)
    if (amount > 0 && amount <= wallet.balance) {
      await stake(wallet.agentId, amount)
      setStakeAmount('')
      setShowStakeModal(false)
    }
  }

  const handleUnstake = async () => {
    const amount = parseFloat(stakeAmount)
    if (amount > 0 && amount <= wallet.stakedAmount) {
      await unstake(wallet.agentId, amount)
      setStakeAmount('')
      setShowStakeModal(false)
    }
  }

  const handleUpdateLimits = async () => {
    const maxTx = parseFloat(maxPerTx)
    const daily = parseFloat(dailyLimit)
    if (maxTx > 0 && daily > 0) {
      await updateLimits(wallet.agentId, maxTx, daily)
      setShowLimitsModal(false)
    }
  }

  const handleDelete = async () => {
    if (confirm(t('agentWallet.confirmDelete', 'Are you sure you want to delete this wallet?'))) {
      await removeWallet(wallet.agentId)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'staked':
        return 'text-green-500'
      case 'unstaking':
        return 'text-yellow-500'
      case 'unlocked':
        return 'text-gray-500'
      default:
        return 'text-gray-400'
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-semibold text-lg">{t('agentWallet.agentId', 'Agent')}: {wallet.agentId.slice(0, 8)}...</h3>
          <p className="text-xs text-gray-500 font-mono">{wallet.walletAddress}</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(wallet.stakeStatus)} bg-opacity-10`}>
          {wallet.stakeStatus}
        </span>
      </div>

      {/* Balance Info */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <p className="text-xs text-gray-500">{t('agentWallet.balance', 'Balance')}</p>
          <p className="text-xl font-bold">{wallet.balance.toLocaleString()} VIBE</p>
        </div>
        <div className="bg-gray-50 dark:bg-gray-700 rounded p-3">
          <p className="text-xs text-gray-500">{t('agentWallet.staked', 'Staked')}</p>
          <p className="text-xl font-bold">{wallet.stakedAmount.toLocaleString()} VIBE</p>
        </div>
      </div>

      {/* Limits Info */}
      <div className="mb-4 text-sm">
        <p><span className="text-gray-500">{t('agentWallet.maxPerTx', 'Max/Tx')}:</span> {wallet.maxPerTx || '∞'}</p>
        <p><span className="text-gray-500">{t('agentWallet.dailyLimit', 'Daily Limit')}:</span> {wallet.dailyLimit || '∞'}</p>
        <p><span className="text-gray-500">{t('agentWallet.remaining', 'Remaining')}:</span> {wallet.remainingDailyLimit >= 0 ? wallet.remainingDailyLimit.toLocaleString() : '∞'}</p>
      </div>

      {/* Actions */}
      {showActions && (
        <div className="flex flex-wrap gap-2">
          <Button size="sm" onClick={() => setShowDepositModal(true)}>
            {t('agentWallet.deposit', 'Deposit')}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setShowTransferModal(true)}>
            {t('agentWallet.transfer', 'Transfer')}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setShowStakeModal(true)}>
            {t('agentWallet.stake', 'Stake')}
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setShowLimitsModal(true)}>
            {t('agentWallet.limits', 'Limits')}
          </Button>
          {onSelect && (
            <Button size="sm" variant="outline" onClick={() => onSelect(wallet)}>
              {t('agentWallet.select', 'Select')}
            </Button>
          )}
          <Button size="sm" variant="danger" onClick={handleDelete}>
            {t('agentWallet.delete', 'Delete')}
          </Button>
        </div>
      )}

      {/* Deposit Modal */}
      {showDepositModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">{t('agentWallet.deposit', 'Deposit')}</h3>
            <label className="block text-sm text-gray-500 mb-1">{t('agentWallet.amount', 'Amount')}</label>
            <Input
              type="number"
              value={depositAmount}
              onChange={(e) => setDepositAmount(e.target.value)}
              placeholder="0"
            />
            <div className="flex gap-2 mt-4">
              <Button onClick={handleDeposit} disabled={isLoading}>
                {t('common.confirm', 'Confirm')}
              </Button>
              <Button variant="secondary" onClick={() => setShowDepositModal(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Transfer Modal */}
      {showTransferModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">{t('agentWallet.transfer', 'Transfer')}</h3>
            <label className="block text-sm text-gray-500 mb-1">{t('agentWallet.toAddress', 'To Address')}</label>
            <Input
              value={transferTo}
              onChange={(e) => setTransferTo(e.target.value)}
              placeholder="0x..."
            />
            <label className="block text-sm text-gray-500 mt-2 mb-1">{t('agentWallet.amount', 'Amount')}</label>
            <Input
              type="number"
              value={transferAmount}
              onChange={(e) => setTransferAmount(e.target.value)}
              placeholder="0"
            />
            <p className="text-xs text-gray-500 mt-2">
              Max: {wallet.maxPerTx || '∞'} per tx, {wallet.remainingDailyLimit >= 0 ? wallet.remainingDailyLimit : '∞'} daily
            </p>
            <div className="flex gap-2 mt-4">
              <Button
                onClick={handleTransfer}
                disabled={isLoading || !canTransfer(wallet, parseFloat(transferAmount) || 0)}
              >
                {t('common.confirm', 'Confirm')}
              </Button>
              <Button variant="secondary" onClick={() => setShowTransferModal(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Stake Modal */}
      {showStakeModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">{t('agentWallet.stake', 'Stake/Unstake')}</h3>
            <label className="block text-sm text-gray-500 mb-1">{t('agentWallet.amount', 'Amount')}</label>
            <Input
              type="number"
              value={stakeAmount}
              onChange={(e) => setStakeAmount(e.target.value)}
              placeholder="0"
            />
            <p className="text-xs text-gray-500 mt-2">
              Available: {wallet.balance} to stake, {wallet.stakedAmount} to unstake
            </p>
            <div className="flex gap-2 mt-4">
              <Button onClick={handleStake} disabled={isLoading}>
                {t('agentWallet.stake', 'Stake')}
              </Button>
              <Button variant="warning" onClick={handleUnstake} disabled={isLoading}>
                {t('agentWallet.unstake', 'Unstake')}
              </Button>
              <Button variant="secondary" onClick={() => setShowStakeModal(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Limits Modal */}
      {showLimitsModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">{t('agentWallet.updateLimits', 'Update Limits')}</h3>
            <label className="block text-sm text-gray-500 mb-1">{t('agentWallet.maxPerTx', 'Max Per Transaction')}</label>
            <Input
              type="number"
              value={maxPerTx}
              onChange={(e) => setMaxPerTx(e.target.value)}
              placeholder="1000"
            />
            <label className="block text-sm text-gray-500 mt-2 mb-1">{t('agentWallet.dailyLimit', 'Daily Limit')}</label>
            <Input
              type="number"
              value={dailyLimit}
              onChange={(e) => setDailyLimit(e.target.value)}
              placeholder="10000"
            />
            <div className="flex gap-2 mt-4">
              <Button onClick={handleUpdateLimits} disabled={isLoading}>
                {t('common.confirm', 'Confirm')}
              </Button>
              <Button variant="secondary" onClick={() => setShowLimitsModal(false)}>
                {t('common.cancel', 'Cancel')}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
