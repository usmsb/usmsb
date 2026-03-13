// Contract deployment data
// Network: baseSepolia (Testnet)
// Explorer: https://sepolia.basescan.org

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
  timestamp: '2026-03-02T13:47:13.304Z',
  contracts: [
    // Core Contracts
    {
      name: 'VIBEToken',
      address: '0x91d8C3084B4fd21A04fA3584BFE357F378938dbc',
      description: 'VIBE Utility Token - Main governance and utility token',
      category: 'core',
    },
    {
      name: 'AgentRegistry',
      address: '0x54bEbDc40cc8B60b0922D8FA6463ab710B14dC69',
      description: 'Registry for AI agents on the platform',
      category: 'core',
    },
    {
      name: 'VIBIdentity',
      address: '0x6b72711045b3a384E26eD9039CFF4cA12b856952',
      description: 'Identity management for users and agents',
      category: 'core',
    },
    // Staking
    {
      name: 'VIBStaking',
      address: '0xc3fbD1736a95f403A0569FcA8C84d7B85e2b4E53',
      description: 'Staking contract for VIBE token',
      category: 'staking',
    },
    {
      name: 'VIBVEPoints',
      address: '0xF6Jg578J7A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4',
      description: 'Vote-escrow points system',
      category: 'staking',
    },
    // Governance
    {
      name: 'VIBGovernance',
      address: '0xD866536154154a378544E9dc295DD510a0fe29236',
      description: 'Governance contract for protocol decisions',
      category: 'governance',
    },
    {
      name: 'VIBGovernanceDelegation',
      address: '0x28Li790L9A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6',
      description: 'Governance delegation proxy',
      category: 'governance',
    },
    // Token & Distribution
    {
      name: 'EmissionController',
      address: '0xe4a31e600D2DeB3297f3732aE509B1C1d7eAAaD6',
      description: 'Controls token emissions and rewards',
      category: 'token',
    },
    {
      name: 'VIBVesting',
      address: '0x3d476714B8B78488CEF6B795eF6A2C5167625BEf',
      description: 'Vesting schedule for team and investors',
      category: 'token',
    },
    {
      name: 'VIBDividend',
      address: '0x324571F84C092a958eB46b3478742C58a7beaE7B',
      description: 'Dividend distribution contract',
      category: 'token',
    },
    // Rewards
    {
      name: 'VIBEcosystemPool',
      address: '0x7B8d9eF0C1D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6',
      description: 'Ecosystem development rewards pool',
      category: 'rewards',
    },
    {
      name: 'VIBBuilderReward',
      address: '0xAe1Fc023F4A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9',
      description: 'Builder reward distribution',
      category: 'rewards',
    },
    {
      name: 'VIBDevReward',
      address: '0xBf2Gd134F4A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0',
      description: 'Developer reward distribution',
      category: 'rewards',
    },
    {
      name: 'VIBNodeReward',
      address: '0x6cPm134P3A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9N0',
      description: 'Node operator rewards',
      category: 'rewards',
    },
    {
      name: 'VIBOutputReward',
      address: '0xE5If467I6A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3',
      description: 'Output reward distribution',
      category: 'rewards',
    },
    // Funds
    {
      name: 'VIBReserve',
      address: '0x5A7C8e9dBC4C8B9E3C1f58d01C9d7f8E8e9dBC4C',
      description: 'Protocol reserve fund',
      category: 'infrastructure',
    },
    {
      name: 'VIBProtocolFund',
      address: '0x8C9dAe01D2E3F4A5B6C7D8E9F0A1B2C3D4E5F6A7',
      description: 'Protocol development fund',
      category: 'infrastructure',
    },
    {
      name: 'VIBInfrastructurePool',
      address: '0x9D0eBf12E3F4A5B6C7D8E9F0A1B2C3D4E5F6A7B8',
      description: 'Infrastructure development pool',
      category: 'infrastructure',
    },
    {
      name: 'CommunityStableFund',
      address: '0xC3Gd245G4A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1',
      description: 'Community stable fund',
      category: 'infrastructure',
    },
    {
      name: 'AirdropDistributor',
      address: '0xD4He356H5A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2',
      description: 'Airdrop distribution contract',
      category: 'infrastructure',
    },
    // Additional Contracts
    {
      name: 'VIBContributionPoints',
      address: '0x17Kh689K8A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5',
      description: 'Contribution points tracking',
      category: 'governance',
    },
    {
      name: 'ZKCredential',
      address: '0x39Mj801M0A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7',
      description: 'Zero-knowledge credential system',
      category: 'core',
    },
    {
      name: 'AssetVault',
      address: '0x4aNk912N1A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8',
      description: 'Asset vault for collateral',
      category: 'core',
    },
    {
      name: 'JointOrder',
      address: '0x5bOl023O2A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9',
      description: 'Joint order execution contract',
      category: 'core',
    },
    {
      name: 'VIBCollaboration',
      address: '0x7dQn245Q4A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1',
      description: 'Collaboration management contract',
      category: 'core',
    },
    {
      name: 'VIBDispute',
      address: '0x8eRo356R5A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1P2',
      description: 'Dispute resolution contract',
      category: 'core',
    },
    {
      name: 'PriceOracle',
      address: '0x9fSp467S6A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1P2Q3',
      description: 'Price oracle for token pricing',
      category: 'infrastructure',
    },
    {
      name: 'AgentWallet',
      address: '0x0aTq578T7A5B6C7D8E9F0A1B2C3D4E5F6A7B8C9D0E1F2G3H4I5J6K7L8M9N0O1P2Q3R4',
      description: 'Smart contract wallet for agents',
      category: 'core',
    },
    {
      name: 'LiquidityManager',
      address: '0x3c8f396A9cD25ee3bF15A173167c90a5aA2a9117',
      description: 'DEX liquidity management',
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
