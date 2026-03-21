import React, { useState } from 'react'
import { useStaking } from '../hooks/useStaking'
import { useAccount } from 'wagmi'

export default function StakingPanel() {
  const { address, isConnected } = useAccount()
  const {
    stakedAmount,
    formattedStakedAmount,
    pendingRewards,
    formattedPendingRewards,
    stake,
    unstake,
    claimReward,
    isLoading,
    isConfirming,
    isConfirmed,
    error,
  } = useStaking()

  const [stakeAmount, setStakeAmount] = useState('')
  const [lockPeriod, setLockPeriod] = useState(1)
  const [txStatus, setTxStatus] = useState<'idle' | 'signing' | 'pending' | 'confirmed' | 'failed'>('idle')

  const handleStake = async () => {
    if (!stakeAmount || parseFloat(stakeAmount) <= 0) return
    setTxStatus('signing')
    try {
      const hash = await stake(stakeAmount, lockPeriod)
      if (hash) {
        setTxStatus('pending')
      } else {
        setTxStatus('failed')
      }
    } catch {
      setTxStatus('failed')
    }
  }

  const handleUnstake = async () => {
    setTxStatus('signing')
    try {
      const hash = await unstake()
      if (hash) {
        setTxStatus('pending')
      } else {
        setTxStatus('failed')
      }
    } catch {
      setTxStatus('failed')
    }
  }

  const handleClaim = async () => {
    setTxStatus('signing')
    try {
      const hash = await claimReward()
      if (hash) {
        setTxStatus('pending')
      } else {
        setTxStatus('failed')
      }
    } catch {
      setTxStatus('failed')
    }
  }

  const resetStatus = () => {
    setTimeout(() => setTxStatus('idle'), 3000)
  }

  if (!isConnected) {
    return (
      <div className="staking-panel">
        <p className="text-gray-400">Connect wallet to view staking info</p>
      </div>
    )
  }

  return (
    <div className="staking-panel p-4 bg-white rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">VIBE Staking</h3>

      {/* Status Banner */}
      {txStatus !== 'idle' && (
        <div className={`mb-4 p-3 rounded ${
          txStatus === 'confirmed' ? 'bg-green-100 text-green-700' :
          txStatus === 'failed' ? 'bg-red-100 text-red-700' :
          txStatus === 'pending' ? 'bg-yellow-100 text-yellow-700' :
          'bg-blue-100 text-blue-700'
        }`}>
          {txStatus === 'signing' && '⏳ Waiting for wallet signature...'}
          {txStatus === 'pending' && '⏳ Transaction submitted, waiting for confirmation...'}
          {txStatus === 'confirmed' && '✅ Transaction confirmed!'}
          {txStatus === 'failed' && '❌ Transaction failed.'}
          {(txStatus === 'confirmed' || txStatus === 'failed') && (
            <button onClick={resetStatus} className="ml-2 text-sm underline">Dismiss</button>
          )}
        </div>
      )}

      {/* Staked Amount */}
      <div className="mb-4">
        <p className="text-sm text-gray-500">Staked Amount</p>
        <p className="text-2xl font-bold">{formattedStakedAmount} <span className="text-sm font-normal">VIBE</span></p>
      </div>

      {/* Pending Rewards */}
      <div className="mb-4">
        <p className="text-sm text-gray-500">Pending Rewards</p>
        <p className="text-xl font-semibold text-green-600">{formattedPendingRewards} <span className="text-sm">VIBE</span></p>
      </div>

      {/* Stake Form */}
      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Amount to Stake</label>
          <input
            type="number"
            value={stakeAmount}
            onChange={(e) => setStakeAmount(e.target.value)}
            placeholder="0.0"
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Lock Period</label>
          <select
            value={lockPeriod}
            onChange={(e) => setLockPeriod(Number(e.target.value))}
            className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={0}>No Lock</option>
            <option value={1}>30 Days</option>
            <option value={2}>90 Days</option>
            <option value={3}>180 Days</option>
            <option value={4}>365 Days</option>
          </select>
        </div>

        <button
          onClick={handleStake}
          disabled={!stakeAmount || parseFloat(stakeAmount) <= 0 || txStatus === 'pending' || txStatus === 'signing'}
          className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {txStatus === 'pending' || txStatus === 'signing' ? 'Processing...' : 'Stake VIBE'}
        </button>

        <button
          onClick={handleUnstake}
          disabled={txStatus === 'pending' || txStatus === 'signing'}
          className="w-full py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {txStatus === 'pending' || txStatus === 'signing' ? 'Processing...' : 'Unstake All'}
        </button>

        <button
          onClick={handleClaim}
          disabled={txStatus === 'pending' || txStatus === 'signing'}
          className="w-full py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {txStatus === 'pending' || txStatus === 'signing' ? 'Processing...' : 'Claim Rewards'}
        </button>
      </div>

      {/* Error */}
      {error && (
        <p className="mt-3 text-sm text-red-600">Error: {error.message}</p>
      )}
    </div>
  )
}
