import { useAccount, useReadContract, useWriteContract, useWaitForTransactionReceipt } from 'wagmi'
import { parseUnits, formatUnits } from 'viem'
import { VIBETOKEN_ABI, VIBETOKEN_ADDRESS } from '@/data/contracts'

export interface UseTokenReturn {
  // Read data
  balance: bigint | undefined
  formattedBalance: string
  tokenName: string | undefined
  tokenSymbol: string | undefined
  tokenDecimals: number | undefined
  totalSupply: bigint | undefined

  // Write functions
  transfer: (to: `0x${string}`, amount: string) => Promise<`0x${string}` | null>
  approve: (spender: `0x${string}`, amount: string) => Promise<`0x${string}` | null>

  // State
  isLoading: boolean
  isConfirming: boolean
  isConfirmed: boolean
  error: Error | null
  hash: `0x${string}` | null
}

const VIBE_DECIMALS = 18

export function useToken(): UseTokenReturn {
  const { address, isConnected } = useAccount()

  // Read balance
  const {
    data: balance,
    isLoading: isBalanceLoading,
    error: balanceError,
  } = useReadContract({
    address: VIBETOKEN_ADDRESS,
    abi: VIBETOKEN_ABI,
    functionName: 'balanceOf',
    args: [address!],
    query: {
      enabled: isConnected && !!address,
    },
  })

  // Read token name
  const { data: tokenName } = useReadContract({
    address: VIBETOKEN_ADDRESS,
    abi: VIBETOKEN_ABI,
    functionName: 'name',
    query: { enabled: isConnected },
  })

  // Read token symbol
  const { data: tokenSymbol } = useReadContract({
    address: VIBETOKEN_ADDRESS,
    abi: VIBETOKEN_ABI,
    functionName: 'symbol',
    query: { enabled: isConnected },
  })

  // Read token decimals
  const { data: tokenDecimals } = useReadContract({
    address: VIBETOKEN_ADDRESS,
    abi: VIBETOKEN_ABI,
    functionName: 'decimals',
    query: { enabled: isConnected },
  })

  // Read total supply
  const { data: totalSupply } = useReadContract({
    address: VIBETOKEN_ADDRESS,
    abi: VIBETOKEN_ABI,
    functionName: 'totalSupply',
    query: { enabled: isConnected },
  })

  // Write contract
  const { data: writeData, writeContract, isPending, error: writeError } = useWriteContract()

  // Wait for transaction
  const { isLoading: isConfirming, isSuccess: isConfirmed } = useWaitForTransactionReceipt({
    hash: writeData,
  })

  // Format balance
  const formattedBalance = balance !== undefined
    ? formatUnits(balance, VIBE_DECIMALS)
    : '0'

  // Transfer function
  const transfer = async (to: `0x${string}`, amount: string): Promise<`0x${string}` | null> => {
    try {
      const parsedAmount = parseUnits(amount, VIBE_DECIMALS)
      writeContract({
        address: VIBETOKEN_ADDRESS,
        abi: VIBETOKEN_ABI,
        functionName: 'transfer',
        args: [to, parsedAmount],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  // Approve function
  const approve = async (spender: `0x${string}`, amount: string): Promise<`0x${string}` | null> => {
    try {
      const parsedAmount = parseUnits(amount, VIBE_DECIMALS)
      writeContract({
        address: VIBETOKEN_ADDRESS,
        abi: VIBETOKEN_ABI,
        functionName: 'approve',
        args: [spender, parsedAmount],
      })
      return writeData ?? null
    } catch {
      return null
    }
  }

  const error = balanceError ?? writeError ?? null

  return {
    balance,
    formattedBalance,
    tokenName: tokenName as string | undefined,
    tokenSymbol: tokenSymbol as string | undefined,
    tokenDecimals: tokenDecimals as number | undefined,
    totalSupply,
    transfer,
    approve,
    isLoading: isBalanceLoading || isPending,
    isConfirming,
    isConfirmed,
    error: error as Error | null,
    hash: writeData ?? null,
  }
}

export default useToken
