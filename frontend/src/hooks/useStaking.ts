import { useAccount, useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { parseUnits, formatUnits } from 'viem'
import { VIBSTAKING_ABI, VIBSTAKING_ADDRESS } from '@/data/contracts'

export interface UseStakingReturn {
  // Read data
  stakedAmount: bigint | undefined
  formattedStakedAmount: string
  pendingRewards: bigint | undefined
  formattedPendingRewards: string

  // Write functions
  stake: (amount: string) => Promise<`0x${string}` | null>
  unstake: (amount: string) => Promise<`0x${string}` | null>
  claimRewards: () => Promise<`0x${string}` | null>

  // State
  isLoading: boolean
  isConfirming: boolean
  isConfirmed: boolean
  error: Error | null
  hash: `0x${string}` | null
}

const VIBE_DECIMALS = 18

export function useStaking(): UseStakingReturn {
  const { address, isConnected } = useAccount()

  // Read staked amount
  const {
    data: stakedAmount,
    isLoading: isStakedLoading,
    error: stakedError,
  } = useReadContract({
    address: VIBSTAKING_ADDRESS,
    abi: VIBSTAKING_ABI,
    functionName: 'getStakedAmount',
    args: [address!],
    query: {
      enabled: isConnected && !!address,
    },
  })

  // Read pending rewards
  const {
    data: pendingRewards,
    isLoading: isRewardsLoading,
    error: rewardsError,
  } = useReadContract({
    address: VIBSTAKING_ADDRESS,
    abi: VIBSTAKING_ABI,
    functionName: 'getPendingRewards',
    args: [address!],
    query: {
      enabled: isConnected && !!address,
    },
  })

  // Write contract
  const { data: writeData, writeContract, isPending, error: writeError } = useWriteContract()

  // Wait for transaction
  const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({
    hash: writeData,
  })

  // Format amounts
  const formattedStakedAmount = stakedAmount !== undefined
    ? formatUnits(stakedAmount, VIBE_DECIMALS)
    : '0'

  const formattedPendingRewards = pendingRewards !== undefined
    ? formatUnits(pendingRewards, VIBE_DECIMALS)
    : '0'

  // Stake function
  const stake = async (amount: string): Promise<`0x${string}` | null> => {
    try {
      const parsedAmount = parseUnits(amount, VIBE_DECIMALS)
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'stake',
        args: [parsedAmount],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  // Unstake function
  const unstake = async (amount: string): Promise<`0x${string}` | null> => {
    try {
      const parsedAmount = parseUnits(amount, VIBE_DECIMALS)
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'unstake',
        args: [parsedAmount],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  // Claim rewards function
  const claimRewards = async (): Promise<`0x${string}` | null> => {
    try {
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'claimRewards',
        args: [],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  const error = stakedError ?? rewardsError ?? writeError ?? null

  return {
    stakedAmount,
    formattedStakedAmount,
    pendingRewards,
    formattedPendingRewards,
    stake,
    unstake,
    claimRewards,
    isLoading: isStakedLoading || isRewardsLoading || isPending,
    isConfirming,
    isConfirmed,
    error: error as Error | null,
    hash: writeData ?? null,
  }
}

export default useStaking
