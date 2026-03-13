import { useState, useCallback, useEffect } from 'react'
import { useAuthStore, AgentWalletInfo } from '@/stores/authStore'
import {
  createAgentWallet,
  getAgentWallet,
  getAgentWallets,
  depositToAgentWallet,
  transferFromAgentWallet,
  stakeAgentWallet,
  unstakeAgentWallet,
  updateAgentWalletLimits,
  deleteAgentWallet,
  CreateAgentWalletRequest,
} from '@/services/authService'

export interface UseAgentWalletReturn {
  // State
  agentWallets: AgentWalletInfo[]
  currentAgentWallet: AgentWalletInfo | null
  isLoading: boolean
  error: string | null

  // Actions
  loadAgentWallets: () => Promise<void>
  createWallet: (agentId: string, agentAddress: string) => Promise<AgentWalletInfo | null>
  selectWallet: (wallet: AgentWalletInfo | null) => void
  deposit: (agentId: string, amount: number) => Promise<boolean>
  transfer: (agentId: string, toAddress: string, amount: number) => Promise<boolean>
  stake: (agentId: string, amount: number) => Promise<boolean>
  unstake: (agentId: string, amount: number) => Promise<boolean>
  updateLimits: (agentId: string, maxPerTx: number, dailyLimit: number) => Promise<boolean>
  removeWallet: (agentId: string) => Promise<boolean>
  refreshWallet: (agentId: string) => Promise<void>

  // Helpers
  canTransfer: (wallet: AgentWalletInfo, amount: number) => boolean
  getRemainingLimit: (wallet: AgentWalletInfo) => number
}

export function useAgentWallet(): UseAgentWalletReturn {
  const {
    agentWallets,
    currentAgentWallet,
    setAgentWallets,
    setCurrentAgentWallet,
    updateAgentWallet,
    accessToken,
  } = useAuthStore()

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load all agent wallets on mount
  const loadAgentWallets = useCallback(async () => {
    if (!accessToken) return

    setIsLoading(true)
    setError(null)
    try {
      const response = await getAgentWallets()
      setAgentWallets(response.wallets)
    } catch (err: any) {
      setError(err.message || 'Failed to load agent wallets')
    } finally {
      setIsLoading(false)
    }
  }, [accessToken, setAgentWallets])

  // Create a new agent wallet
  const createWallet = useCallback(async (
    agentId: string,
    agentAddress: string
  ): Promise<AgentWalletInfo | null> => {
    setIsLoading(true)
    setError(null)
    try {
      const data: CreateAgentWalletRequest = {
        agent_id: agentId,
        agent_address: agentAddress,
      }
      const response = await createAgentWallet(data)

      // Refresh wallets list
      await loadAgentWallets()

      return {
        agentId: response.agentId,
        walletAddress: response.walletAddress,
        agentAddress: response.agentAddress,
        balance: response.balance,
        stakedAmount: response.stakedAmount,
        stakeStatus: response.stakeStatus,
        maxPerTx: 0,
        dailyLimit: 0,
        dailySpent: 0,
        remainingDailyLimit: 0,
        isRegistered: true,
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create agent wallet')
      return null
    } finally {
      setIsLoading(false)
    }
  }, [loadAgentWallets])

  // Select current wallet
  const selectWallet = useCallback((wallet: AgentWalletInfo | null) => {
    setCurrentAgentWallet(wallet)
  }, [setCurrentAgentWallet])

  // Deposit to agent wallet
  const deposit = useCallback(async (agentId: string, amount: number): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await depositToAgentWallet(agentId, amount)
      if (response.success) {
        updateAgentWallet(agentId, {
          balance: response.newBalance,
          stakedAmount: response.newStakedAmount,
        })
        return true
      }
      setError(response.message)
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to deposit')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [updateAgentWallet])

  // Transfer from agent wallet
  const transfer = useCallback(async (
    agentId: string,
    toAddress: string,
    amount: number
  ): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await transferFromAgentWallet(agentId, toAddress, amount)
      if (response.success) {
        updateAgentWallet(agentId, {
          balance: response.newBalance,
        })
        return true
      }
      setError(response.message)
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to transfer')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [updateAgentWallet])

  // Stake from agent wallet
  const stake = useCallback(async (agentId: string, amount: number): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await stakeAgentWallet(agentId, amount)
      if (response.success) {
        updateAgentWallet(agentId, {
          balance: response.newBalance,
          stakedAmount: response.newStakedAmount,
          stakeStatus: 'staked',
        })
        return true
      }
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to stake')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [updateAgentWallet])

  // Unstake from agent wallet


  const unstake = useCallback(async (agentId: string, amount: number): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await unstakeAgentWallet(agentId, amount)
      if (response.success) {
        updateAgentWallet(agentId, {
          stakeStatus: 'unstaking',
          unlockAvailableAt: response.unlockAvailableAt,
        })
        return true
      }
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to unstake')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [updateAgentWallet])

  // Update agent wallet limits
  const updateLimits = useCallback(async (
    agentId: string,
    maxPerTx: number,
    dailyLimit: number
  ): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await updateAgentWalletLimits(agentId, maxPerTx, dailyLimit)
      if (response.success) {
        updateAgentWallet(agentId, {
          maxPerTx,
          dailyLimit,
          remainingDailyLimit: dailyLimit,
        })
        return true
      }
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to update limits')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [updateAgentWallet])

  // Delete agent wallet
  const removeWallet = useCallback(async (agentId: string): Promise<boolean> => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await deleteAgentWallet(agentId)
      if (response.success) {
        // Remove from local state
        const newWallets = agentWallets.filter(w => w.agentId !== agentId)
        setAgentWallets(newWallets)

        // Clear current if it was deleted
        if (currentAgentWallet?.agentId === agentId) {
          setCurrentAgentWallet(null)
        }
        return true
      }
      return false
    } catch (err: any) {
      setError(err.message || 'Failed to delete wallet')
      return false
    } finally {
      setIsLoading(false)
    }
  }, [agentWallets, currentAgentWallet, setAgentWallets, setCurrentAgentWallet])

  // Refresh single wallet info
  const refreshWallet = useCallback(async (agentId: string) => {
    try {
      const wallet = await getAgentWallet(agentId)
      updateAgentWallet(agentId, wallet)
    } catch (err: any) {
      console.error('Failed to refresh wallet:', err)
    }
  }, [updateAgentWallet])

  // Helper: Check if transfer is allowed within limits
  const canTransfer = useCallback((wallet: AgentWalletInfo, amount: number): boolean => {
    if (amount <= 0) return false
    if (wallet.balance < amount) return false
    if (wallet.maxPerTx > 0 && amount > wallet.maxPerTx) return false
    if (wallet.remainingDailyLimit > 0 && amount > wallet.remainingDailyLimit) return false
    return true
  }, [])

  // Helper: Get remaining daily limit
  const getRemainingLimit = useCallback((wallet: AgentWalletInfo): number => {
    if (wallet.dailyLimit <= 0) return -1 // Unlimited
    return wallet.remainingDailyLimit
  }, [])

  // Load wallets on mount when user is logged in
  useEffect(() => {
    if (accessToken) {
      loadAgentWallets()
    }
  }, [accessToken, loadAgentWallets])

  return {
    agentWallets,
    currentAgentWallet,
    isLoading,
    error,
    loadAgentWallets,
    createWallet,
    selectWallet,
    deposit,
    transfer,
    stake,
    unstake,
    updateLimits,
    removeWallet,
    refreshWallet,
    canTransfer,
    getRemainingLimit,
  }
}
