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
  // lockPeriod: 0=NONE, 1=THIRTY(30d), 2=NINETY(90d), 3=ONE80(180d), 4=ONE_YEAR(365d)
  stake: (amount: string, lockPeriod: number) => Promise<`0x${string}` | null>
  unstake: () => Promise<`0x${string}` | null>
  claimReward: () => Promise<`0x${string}` | null>

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

  // Read staked amount via getStakeInfo which returns (amount, startTime, lockPeriod, isActive)
  const {
    data: stakeInfo,
    isLoading: isStakedLoading,
    error: stakedError,
  } = useReadContract({
    address: VIBSTAKING_ADDRESS,
    abi: VIBSTAKING_ABI,
    functionName: 'getStakeInfo',
    args: [address!],
    query: {
      enabled: isConnected && !!address,
    },
  })

  // Extract staked amount from the struct (index 0 = amount)
  const stakedAmount = stakeInfo ? (stakeInfo[0] as bigint) : undefined

  // Read pending rewards
  const {
    data: pendingRewards,
    isLoading: isRewardsLoading,
    error: rewardsError,
  } = useReadContract({
    address: VIBSTAKING_ADDRESS,
    abi: VIBSTAKING_ABI,
    functionName: 'getPendingReward',
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

  // Stake function — lockPeriod: 0=NONE, 1=THIRTY(30d), 2=NINETY(90d), 3=ONE80(180d), 4=ONE_YEAR(365d)
  const stake = async (amount: string, lockPeriod: number): Promise<`0x${string}` | null> => {
    try {
      const parsedAmount = parseUnits(amount, VIBE_DECIMALS)
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'stake',
        args: [parsedAmount, BigInt(lockPeriod)],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  // Unstake function — unstakes ALL (contract takes no parameters)
  const unstake = async (): Promise<`0x${string}` | null> => {
    try {
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'unstake',
        args: [],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  // Claim rewards function
  const claimReward = async (): Promise<`0x${string}` | null> => {
    try {
      writeContract({
        address: VIBSTAKING_ADDRESS,
        abi: VIBSTAKING_ABI,
        functionName: 'claimReward',
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
    claimReward,
    isLoading: isStakedLoading || isRewardsLoading || isPending,
    isConfirming,
    isConfirmed,
    error: error as Error | null,
    hash: writeData ?? null,
  }
}

export default useStaking
