// useMulticall3.ts - Multicall3 批量链上读取 Hook
import { useQuery } from '@tanstack/react-query'
import { BrowserProvider, Contract } from 'ethers'

const MULTICALL3_ADDRESS = '0xcA11bde05977b3631167028862bE2a173976CA11'

// Multicall3 ABI (仅 relevant calls)
const MULTICALL3_ABI = [
  {
    type: 'struct',
    name: 'Call3',
    inputs: [
      { name: 'target', type: 'address' },
      { name: 'allowFailure', type: 'bool' },
      { name: 'callData', type: 'bytes' },
    ],
  },
  {
    type: 'function',
    name: 'aggregate3',
    inputs: [{ name: 'calls', type: 'Call3[]' }],
    outputs: [
      {
        type: 'struct Result[]',
        name: 'returnData',
        components: [
          { name: 'success', type: 'bool' },
          { name: 'returnData', type: 'bytes' },
        ],
      },
    ],
    stateMutability: 'payable',
  },
]

interface MulticallCall {
  id: string
  address: string
  abi: unknown[]
  method: string
  args?: unknown[]
}

interface UseMulticall3Options {
  calls: MulticallCall[]
  enabled?: boolean
  refetchInterval?: number
}

interface MulticallResult {
  id: string
  success: boolean
  data?: string
  decoded?: unknown
  error?: string
}

function encodeCall(abi: unknown[], method: string, args: unknown[] = []): string {
  try {
    const iface = new Contract('0x0000000000000000000000000000000000000001', abi as any)
    return iface.interface.encodeFunctionData(method, args)
  } catch {
    return '0x'
  }
}

function decodeResult(abi: unknown[], method: string, data: string): unknown {
  try {
    const iface = new Contract('0x0000000000000000000000000000000000000001', abi as any)
    return iface.interface.decodeFunctionResult(method, data)
  } catch {
    return null
  }
}

export function useMulticall3({ calls, enabled = true, refetchInterval }: UseMulticall3Options) {
  return useQuery({
    queryKey: ['multicall3', calls.map(c => c.id)],
    queryFn: async (): Promise<MulticallResult[]> => {
      const provider = new BrowserProvider(window.ethereum as any)
      const multicall = new Contract(MULTICALL3_ADDRESS, MULTICALL3_ABI, provider)

      const encodedCalls = calls.map(call => ({
        target: call.address,
        allowFailure: true,
        callData: encodeCall(call.abi, call.method, call.args || []),
      }))

      const results = await multicall.aggregate3(encodedCalls)

      return calls.map((call, i) => {
        const result = results[i]
        if (!result.success) {
          return { id: call.id, success: false, error: 'Call failed' }
        }
        return {
          id: call.id,
          success: true,
          data: result.returnData,
          decoded: decodeResult(call.abi, call.method, result.returnData),
        }
      })
    },
    enabled: enabled && calls.length > 0 && !!window.ethereum,
    refetchInterval,
    retry: 1,
  })
}

// 辅助：批量读取 staking 数据
export function useStakingMulticall(addresses: string[], stakingAddress: string, stakingAbi: unknown[]) {
  const calls: MulticallCall[] = addresses.map(addr => ({
    id: `staker-${addr}`,
    address: stakingAddress,
    abi: stakingAbi,
    method: 'stakerInfo',
    args: [addr],
  }))

  const { data, isLoading, error } = useMulticall3({ calls })

  return {
    results: data ?? [],
    isLoading,
    error,
    getStakerInfo: (addr: string) => data?.find(r => r.id === `staker-${addr}`)?.decoded,
  }
}
