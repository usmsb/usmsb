// hooks/useBlockchain.ts - 区块链数据读取 (ethers.js v6)
import { useQuery } from '@tanstack/react-query'
import { BrowserProvider, Contract, formatEther, formatUnits } from 'ethers'
import { CONTRACTS, CHAIN_CONFIG } from '../contracts/addresses'

// 加载 ABI
function loadABI(name: string): any {
  try {
    const abi = require(`../contracts/abis/${name}.json`)
    return abi.abi || abi
  } catch {
    return []
  }
}

// 获取 provider
function getProvider(): BrowserProvider | null {
  if (!window.ethereum) return null
  return new BrowserProvider(window.ethereum as never)
}

// 通用合约读取
async function readContract(contractName: string, method: string, args: unknown[] = [], chain: keyof typeof CONTRACTS = 'baseSepolia') {
  const provider = getProvider()
  if (!provider) throw new Error('No wallet connected')

  const address = CONTRACTS[chain][contractName as keyof typeof CONTRACTS[typeof chain]]
  if (!address) throw new Error(`Unknown contract: ${contractName}`)

  const abi = loadABI(contractName)
  const contract = new Contract(address, abi, provider)
  const result = await contract[method](...args)
  return result
}

// ── Staking 读取 ──────────────────────────────────────────────
export function useStakingStats() {
  return useQuery({
    queryKey: ['blockchain', 'staking', 'stats'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return null

      const stakingAddr = CONTRACTS.baseSepolia.VIBStaking
      const tokenAddr = CONTRACTS.baseSepolia.VIBEToken
      const stakingABI = loadABI('VIBStaking')
      const tokenABI = loadABI('VIBEToken')

      const staking = new Contract(stakingAddr, stakingABI, provider)
      const token = new Contract(tokenAddr, tokenABI, provider)

      const [totalStaked, tokenBalance, stakingTokenBalance, rewardRate, apr] = await Promise.all([
        staking.totalStaked().catch(() => 0n),
        token.balanceOf(stakingAddr).catch(() => 0n),
        staking.totalStaked().catch(() => 0n),
        staking.rewardRate().catch(() => 0n),
        staking.apr().catch(() => 0n),
      ])

      return {
        total_staked: formatEther(totalStaked || 0n),
        reward_pool: formatEther(tokenBalance || 0n),
        reward_rate: formatEther(rewardRate || 0n),
        apr: apr ? Number(formatUnits(apr, 2)) / 100 : 0,
        validator_count: 0,
      }
    },
    refetchInterval: 60000,
    retry: 1,
  })
}

export function useStakingTiers() {
  return useQuery({
    queryKey: ['blockchain', 'staking', 'tiers'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return []

      const stakingAddr = CONTRACTS.baseSepolia.VIBStaking
      const staking = new Contract(stakingAddr, loadABI('VIBStaking'), provider)

      // tierThresholds / tierInfo by index
      const tiers = await Promise.allSettled(
        [0, 1, 2, 3, 4].map(i =>
          staking.tierInfo(i).catch(() => null)
        )
      )

      return tiers
        .map((r, i) => {
          if (r.status !== 'fulfilled' || !r.value) return null
          const info = r.value as { minStake: bigint; multiplier: bigint; label: string }
          return {
            tier: i,
            label: String(info.label || `Tier ${i}`),
            min_stake: formatEther(info.minStake || 0n),
            multiplier: Number(formatUnits(info.multiplier || 0n, 2)) / 100,
          }
        })
        .filter(Boolean)
    },
    refetchInterval: 120000,
    retry: 1,
  })
}

export function useStakerInfo(address: string) {
  return useQuery({
    queryKey: ['blockchain', 'staking', 'staker', address],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider || !address) return null

      const staking = new Contract(CONTRACTS.baseSepolia.VIBStaking, loadABI('VIBStaking'), provider)
      const info = await staking.stakerInfo(address).catch(() => null)
      if (!info) return null

      return {
        stake: formatEther(info[0] || 0n),
        tier: Number(info[1] || 0),
        start_time: Number(info[2] || 0),
        rewards_claimed: formatEther(info[3] || 0n),
        pending_rewards: formatEther(info[4] || 0n),
      }
    },
    enabled: !!address,
    refetchInterval: 30000,
    retry: 1,
  })
}

// ── Governance 读取 ──────────────────────────────────────────
export function useGovernanceStats() {
  return useQuery({
    queryKey: ['blockchain', 'governance', 'stats'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return null

      const gov = new Contract(CONTRACTS.baseSepolia.VIBGovernance, loadABI('VIBGovernance'), provider)
      const delegation = new Contract(CONTRACTS.baseSepolia.VIBGovernanceDelegation, loadABI('VIBGovernanceDelegation'), loadABI('VIBVEPoints'))

      const [proposalCount, totalDelegated, veTokenTotal, quorum] = await Promise.allSettled([
        gov.proposalCount().catch(() => 0n),
        delegation.totalDelegated().catch(() => 0n),
        gov.veTokenTotalSupply().catch(() => 0n),
        gov.quorumVotes().catch(() => 0n),
      ])

      return {
        proposal_count: proposalCount.status === 'fulfilled' ? Number(proposalCount.value || 0n) : 0,
        total_delegated: totalDelegated.status === 'fulfilled' ? formatEther(totalDelegated.value || 0n) : '0',
        ve_token_supply: veTokenTotal.status === 'fulfilled' ? formatEther(veTokenTotal.value || 0n) : '0',
        quorum_votes: quorum.status === 'fulfilled' ? formatEther(quorum.value || 0n) : '0',
      }
    },
    refetchInterval: 300000,
    retry: 1,
  })
}

export function useProposalList() {
  return useQuery({
    queryKey: ['blockchain', 'governance', 'proposals'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return []

      const gov = new Contract(CONTRACTS.baseSepolia.VIBGovernance, loadABI('VIBGovernance'), provider)
      const count = Number(await gov.proposalCount().catch(() => 0n))

      const proposals = await Promise.allSettled(
        Array.from({ length: Math.min(count, 20) }, (_, i) =>
          gov.getProposal(i + 1).catch(() => null)
        )
      )

      return proposals
        .map((r, i) => {
          if (r.status !== 'fulfilled' || !r.value) return null
          const p = r.value as { id: bigint; proposer: string; description: string; forVotes: bigint; againstVotes: bigint; deadline: bigint; executed: boolean; }
          return {
            id: Number(p.id || BigInt(i + 1)),
            proposer: p.proposer || '',
            description: String(p.description || '').slice(0, 80),
            for_votes: formatEther(p.forVotes || 0n),
            against_votes: formatEther(p.againstVotes || 0n),
            deadline: Number(p.deadline || 0n),
            executed: p.executed || false,
          }
        })
        .filter(Boolean)
    },
    refetchInterval: 300000,
    retry: 1,
  })
}

// ── Token 读取 ──────────────────────────────────────────────
export function useTokenBalance(address: string) {
  return useQuery({
    queryKey: ['blockchain', 'token', 'balance', address],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider || !address) return null

      const token = new Contract(CONTRACTS.baseSepolia.VIBEToken, loadABI('VIBEToken'), provider)
      const [rawBalance, totalSupply, decimals] = await Promise.all([
        token.balanceOf(address).catch(() => 0n),
        token.totalSupply().catch(() => 0n),
        token.decimals().catch(() => 18),
      ])

      return {
        balance: formatEther(rawBalance || 0n),
        total_supply: formatEther(totalSupply || 0n),
        decimals: Number(decimals || 18),
      }
    },
    enabled: !!address,
    refetchInterval: 60000,
    retry: 1,
  })
}

// ── 奖励合约读取 ──────────────────────────────────────────────
export function useRewardContracts() {
  return useQuery({
    queryKey: ['blockchain', 'rewards'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return []

      const contracts = [
        { name: 'VIBBuilderReward', addr: CONTRACTS.baseSepolia.VIBBuilderReward, abi: 'VIBBuilderReward' },
        { name: 'VIBDevReward', addr: CONTRACTS.baseSepolia.VIBDevReward, abi: 'VIBDevReward' },
        { name: 'VIBNodeReward', addr: CONTRACTS.baseSepolia.VIBNodeReward, abi: 'VIBNodeReward' },
        { name: 'VIBOutputReward', addr: CONTRACTS.baseSepolia.VIBOutputReward, abi: 'VIBOutputReward' },
        { name: 'VIBDividend', addr: CONTRACTS.baseSepolia.VIBDividend, abi: 'VIBDividend' },
      ]

      return Promise.all(
        contracts.map(async c => {
          try {
            const token = new Contract(CONTRACTS.baseSepolia.VIBEToken, loadABI('VIBEToken'), provider)
            const balance = await token.balanceOf(c.addr).catch(() => 0n)
            return { name: c.name, address: c.addr, pool: formatEther(balance || 0n), status: 'active' }
          } catch {
            return { name: c.name, address: c.addr, pool: '0', status: 'unknown' }
          }
        })
      )
    },
    refetchInterval: 120000,
    retry: 1,
  })
}

// ── 协作合约读取 ──────────────────────────────────────────────
export function useCollaborationStats() {
  return useQuery({
    queryKey: ['blockchain', 'collaboration'],
    queryFn: async () => {
      const provider = getProvider()
      if (!provider) return null

      const collab = new Contract(CONTRACTS.baseSepolia.VIBCollaboration, loadABI('VIBCollaboration'), provider)
      const [activeCount, totalVolume, avgReward] = await Promise.allSettled([
        collab.activeCollaborationCount().catch(() => 0n),
        collab.totalVolume().catch(() => 0n),
        collab.averageReward().catch(() => 0n),
      ])

      return {
        active_collaborations: activeCount.status === 'fulfilled' ? Number(activeCount.value || 0n) : 0,
        total_volume: totalVolume.status === 'fulfilled' ? formatEther(totalVolume.value || 0n) : '0',
        avg_reward: avgReward.status === 'fulfilled' ? formatEther(avgReward.value || 0n) : '0',
      }
    },
    refetchInterval: 120000,
    retry: 1,
  })
}

// helper for total count
const totalCount = { value: 0n }
