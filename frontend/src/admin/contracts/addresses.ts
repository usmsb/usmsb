// contracts/addresses.ts - Base Sepolia 合约地址

export const CONTRACTS = {
  baseSepolia: {
    // Core
    VIBEToken: '0x93C52dF000317e12F891474B46d8B05652430bDC',
    VIBStaking: '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05',
    VIBGovernance: '0x27475aea1eEba485005B1717a35a7D411d144a1d',
    VIBVesting: '0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924',
    VIBReserve: '0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263',
    VIBProtocolFund: '0x0F39011e7E542D939C1dce40754a86b01BB3fA5a',
    // Rewards
    VIBBuilderReward: '0x397Faf7D727db190fB677362B15c091f1d94F7b3',
    VIBDevReward: '0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E',
    VIBNodeReward: '0xc417b180F3b743A51e86c16A8319Eac353fDC29b',
    VIBOutputReward: '0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b',
    VIBDividend: '0xa820F9E9Caa90e405452Fc3f24DC5DF7f7d70E9D',
    // Ecosystem
    VIBInfrastructurePool: '0xFc2943d6D426D4D6433944e1ADa4D475F3552500',
    VIBEcosystemPool: '0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06',
    // Identity & Registry
    VIBIdentity: '0x978eddDf11728B4e6A6C461D8806eD5f4339D466',
    AgentRegistry: '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6',
    // Collaboration
    VIBCollaboration: '0xe568c56f467E27Cb38d4B132B02318C81EC29D78',
    // Market
    PriceOracle: '0x20306509a6b2f0b56ad55C193b4505CA5E62bc48',
    AssetVault: '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897',
    JointOrder: '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0',
    ZKCredential: '0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874',
    // Points
    VIBContributionPoints: '0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5',
    VIBGovernanceDelegation: '0x47428bAB428966B32F246a3e9456f10dc70141A5',
    // Automation
    AirdropDistributor: '0x01cdC2C7C3Deb071e6C7B42ED66884DDd3CADDf6',
    CommunityStableFund: '0x6e616E6B1d63709dA849074bb7cd5A6936350563',
    LiquidityManager: '0x5c11b7f74bBb2dbBE232C6A456eCa64DA4722D42',
    EmissionController: '0xAbCdEf1234567890FEDcBa09876543210fEdCbAe',
  },
} as const

export const CHAIN_CONFIG = {
  baseSepolia: {
    chainId: 84532,
    name: 'Base Sepolia',
    rpcUrl: 'https://sepolia.base.org',
    blockExplorer: 'https://sepolia.basescan.org',
    multicall3: '0xcA11bde05977b3631167028862bE2a173976CA11',
  },
} as const

export type ChainName = keyof typeof CONTRACTS
