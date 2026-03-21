// Contract deployment data
// Network: baseSepolia (Testnet)
// Explorer: https://sepolia.basescan.org
// Deployed: 2026-03-19
// VIBEToken: 0x93C52dF000317e12F891474B46d8B05652430bDC

// ============================================
// Minimal ABIs for frontend blockchain interaction
// ============================================

export const VIBETOKEN_ABI = [
  {
    name: 'balanceOf',
    type: 'function',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    name: 'name',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
    stateMutability: 'view',
  },
  {
    name: 'symbol',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'string' }],
    stateMutability: 'view',
  },
  {
    name: 'decimals',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'uint8' }],
    stateMutability: 'view',
  },
  {
    name: 'transfer',
    type: 'function',
    inputs: [
      { name: 'to', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
  },
  {
    name: 'approve',
    type: 'function',
    inputs: [
      { name: 'spender', type: 'address' },
      { name: 'amount', type: 'uint256' },
    ],
    outputs: [{ name: '', type: 'bool' }],
    stateMutability: 'nonpayable',
  },
  {
    name: 'allowance',
    type: 'function',
    inputs: [
      { name: 'owner', type: 'address' },
      { name: 'spender', type: 'address' },
    ],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    name: 'totalSupply',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
] as const

export const VIBSTAKING_ABI = [
  {
    name: 'getStakedAmount',
    type: 'function',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    name: 'getPendingRewards',
    type: 'function',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    name: 'stake',
    type: 'function',
    inputs: [{ name: 'amount', type: 'uint256' }],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    name: 'unstake',
    type: 'function',
    inputs: [{ name: 'amount', type: 'uint256' }],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    name: 'claimRewards',
    type: 'function',
    inputs: [],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    name: 'rewardToken',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'address' }],
    stateMutability: 'view',
  },
  {
    name: 'stakingToken',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'address' }],
    stateMutability: 'view',
  },
] as const

export const VIBGOVERNANCE_ABI = [
  {
    name: 'proposalCount',
    type: 'function',
    inputs: [],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
  {
    name: 'getProposal',
    type: 'function',
    inputs: [{ name: 'proposalId', type: 'uint256' }],
    outputs: [
      {
        type: 'tuple',
        name: '',
        components: [
          { name: 'id', type: 'uint256' },
          { name: 'proposer', type: 'address' },
          { name: 'title', type: 'string' },
          { name: 'description', type: 'string' },
          { name: 'forVotes', type: 'uint256' },
          { name: 'againstVotes', type: 'uint256' },
          { name: 'startTime', type: 'uint256' },
          { name: 'endTime', type: 'uint256' },
          { name: 'executed', type: 'bool' },
          { name: 'cancelled', type: 'bool' },
        ],
      },
    ],
    stateMutability: 'view',
  },
  {
    name: 'castVote',
    type: 'function',
    inputs: [
      { name: 'proposalId', type: 'uint256' },
      { name: 'support', type: 'bool' },
    ],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    name: 'getVotes',
    type: 'function',
    inputs: [{ name: 'account', type: 'address' }],
    outputs: [{ name: '', type: 'uint256' }],
    stateMutability: 'view',
  },
] as const

export const JOINTORDER_ABI = [
  {
    name: 'createOrder',
    type: 'function',
    inputs: [
      { name: 'serviceId', type: 'uint256' },
      { name: 'agentId', type: 'uint256' },
      { name: 'clientId', type: 'uint256' },
      { name: 'amount', type: 'uint256' },
      { name: 'requirements', type: 'string' },
    ],
    outputs: [{ name: 'orderId', type: 'uint256' }],
    stateMutability: 'nonpayable',
  },
  {
    name: 'confirmDelivery',
    type: 'function',
    inputs: [{ name: 'orderId', type: 'uint256' }],
    outputs: [],
    stateMutability: 'nonpayable',
  },
  {
    name: 'raiseDispute',
    type: 'function',
    inputs: [{ name: 'orderId', type: 'uint256' }],
    outputs: [],
    stateMutability: 'nonpayable',
  },
] as const

// Contract address exports
export const VIBETOKEN_ADDRESS = '0x93C52dF000317e12F891474B46d8B05652430bDC'
export const VIBSTAKING_ADDRESS = '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05'
export const VIBGOVERNANCE_ADDRESS = '0x27475aea1eEba485005B1717a35a7D411d144a1d'
export const VIBVESTING_ADDRESS = '0x4d3008550fc164ccf0e1C0C4f666EFC14dE924'
export const JOINTORDER_ADDRESS = '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0'
export const VIBIDENTITY_ADDRESS = '0x978eddDf11728B4e6A6C461D8806eD5f4339D466'
export const AGENTREGISTRY_ADDRESS = '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6'
export const AGENTWALLET_ADDRESS = '0xeAd5FCC931493F702208B737528578718D681243'

export interface ContractInfo {
  name: string
  address: string
  description: string
  category: 'core' | 'token' | 'staking' | 'governance' | 'rewards' | 'infrastructure'
}

export interface DeploymentData {
  network: string
  networkName: string
  explorerUrl: string
  deployer: string
  timestamp: string
  contracts: ContractInfo[]
}

export const deploymentData: DeploymentData = {
  network: 'baseSepolia',
  networkName: 'Base Sepolia Testnet',
  explorerUrl: 'https://sepolia.basescan.org',
  deployer: '0x382B71e8b425CFAaD1B1C6D970481F440458Abf8',
  timestamp: '2026-03-19T15:43:00.000Z',
  contracts: [
    // Core Token
    {
      name: 'VIBEToken',
      address: '0x93C52dF000317e12F891474B46d8B05652430bDC',
      description: 'VIBE Utility Token - 1B total supply, whitepaper 10000bps distribution',
      category: 'core',
    },
    // Staking & Vesting
    {
      name: 'VIBStaking',
      address: '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05',
      description: 'Staking contract - receives 28.35% = 283.5M VIBE',
      category: 'staking',
    },
    {
      name: 'VIBVesting',
      address: '0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924',
      description: 'Vesting for team (8%) + early supporters (4%)',
      category: 'staking',
    },
    {
      name: 'VIBReserve',
      address: '0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263',
      description: 'Reserve pool - receives 6.3% = 63M VIBE',
      category: 'staking',
    },
    // Governance
    {
      name: 'VIBGovernance',
      address: '0x27475aea1eEba485005B1717a35a7D411d144a1d',
      description: 'Governance - receives 9.45% = 94.5M VIBE',
      category: 'governance',
    },
    {
      name: 'VIBGovernanceDelegation',
      address: '0x47428bAB428966B32F246a3e9456f10dc70141A5',
      description: 'Governance delegation proxy',
      category: 'governance',
    },
    {
      name: 'VIBContributionPoints',
      address: '0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5',
      description: 'Contribution points tracking',
      category: 'governance',
    },
    {
      name: 'VIBVEPoints',
      address: '0xB2b56dce955ab200E0c1888C22Ac711803e607F1',
      description: 'Vote-escrowed points system',
      category: 'governance',
    },
    {
      name: 'VIBDispute',
      address: '0xE32d99daDBd4443423EfDc590af7591f84FAFE7e',
      description: 'Dispute resolution contract',
      category: 'governance',
    },
    // Token & Distribution
    {
      name: 'VIBDividend',
      address: '0xa820F9E9Caa90e405452Fc3f24DC5DF7f7d70E9D',
      description: 'Dividend distribution contract',
      category: 'token',
    },
    {
      name: 'EmissionController',
      address: '0xaeD496480c9668dc90Dc309fCD8Fd9aE4268dF39',
      description: 'Controls token emissions and rewards',
      category: 'token',
    },
    {
      name: 'VIBEcosystemPool',
      address: '0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06',
      description: 'Ecosystem pool - receives 18.9% = 189M VIBE',
      category: 'token',
    },
    {
      name: 'AirdropDistributor',
      address: '0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6',
      description: 'Airdrop distribution - receives 7% = 70M VIBE',
      category: 'token',
    },
    {
      name: 'CommunityStableFund',
      address: '0x6e616E6B1d63709dA849074bb7cd5A6936350563',
      description: 'Community stable fund - receives 6% = 60M VIBE',
      category: 'token',
    },
    {
      name: 'LiquidityManager',
      address: '0x5c11b7f74bBb2dbBE232C6A456eCa64DA4722D42',
      description: 'DEX liquidity management - receives 12% = 120M VIBE',
      category: 'token',
    },
    // Rewards
    {
      name: 'VIBBuilderReward',
      address: '0x397Faf7D727db190fB677362B15c091f1d94F7b3',
      description: 'Builder reward distribution',
      category: 'rewards',
    },
    {
      name: 'VIBDevReward',
      address: '0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E',
      description: 'Developer reward distribution',
      category: 'rewards',
    },
    {
      name: 'VIBNodeReward',
      address: '0xc417b180F3b743A51e86c16A8319Eac353fDC29b',
      description: 'Node operator rewards',
      category: 'rewards',
    },
    {
      name: 'VIBOutputReward',
      address: '0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b',
      description: 'Output reward distribution',
      category: 'rewards',
    },
    // Funds
    {
      name: 'VIBProtocolFund',
      address: '0x0F39011e7E542D939C1dce40754a86b01BB3fA5a',
      description: 'Protocol development fund',
      category: 'infrastructure',
    },
    {
      name: 'VIBInfrastructurePool',
      address: '0xFc2943d6D426D4D6433944e1ADa4D475F3552500',
      description: 'Infrastructure development pool',
      category: 'infrastructure',
    },
    // Core System
    {
      name: 'VIBIdentity',
      address: '0x978eddDf11728B4e6A6C461D8806eD5f4339D466',
      description: 'Identity management for users and agents',
      category: 'core',
    },
    {
      name: 'VIBCollaboration',
      address: '0xe568c56f467E27Cb38d4B132B02318C81EC29D78',
      description: 'Collaboration management contract',
      category: 'core',
    },
    {
      name: 'AgentRegistry',
      address: '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6',
      description: 'Registry for AI agents on the platform',
      category: 'core',
    },
    {
      name: 'AgentWallet',
      address: '0xeAd5FCC931493F702208B737528578718D681243',
      description: 'Smart contract wallet for agents',
      category: 'core',
    },
    {
      name: 'ZKCredential',
      address: '0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874',
      description: 'Zero-knowledge credential system',
      category: 'core',
    },
    {
      name: 'AssetVault',
      address: '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897',
      description: 'Asset vault for collateral',
      category: 'core',
    },
    {
      name: 'JointOrder',
      address: '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0',
      description: 'Joint order execution contract',
      category: 'core',
    },
    {
      name: 'PriceOracle',
      address: '0x20306509a6b2f0b56ad55C193b4505CA5E62bc48',
      description: 'Price oracle for token pricing',
      category: 'infrastructure',
    },
  ],
}

export const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    core: 'blue',
    token: 'purple',
    staking: 'green',
    governance: 'yellow',
    rewards: 'orange',
    infrastructure: 'cyan',
  }
  return colors[category] || 'gray'
}

export const getCategoryLabel = (category: string): string => {
  const labels: Record<string, string> = {
    core: 'Core',
    token: 'Token',
    staking: 'Staking',
    governance: 'Governance',
    rewards: 'Rewards',
    infrastructure: 'Infrastructure',
  }
  return labels[category] || category
}
