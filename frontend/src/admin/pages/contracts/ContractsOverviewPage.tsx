/** ContractsOverviewPage - 合约总览 */
import { Hexagon } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'
import { Link } from 'react-router-dom'

const contractCategories = [
  {
    title: '质押生态',
    path: '/admin/contracts/staking',
    description: 'VIBStaking / Dividend / VE / Emission',
    color: 'primary',
  },
  {
    title: '奖励分发',
    path: '/admin/contracts/rewards',
    description: 'Builder / Dev / Node / Output / Collaboration',
    color: 'success',
  },
  {
    title: '治理合约',
    path: '/admin/contracts/governance',
    description: 'Governance / Delegation / Contribution / Dispute',
    color: 'info',
  },
  {
    title: '市场数据',
    path: '/admin/contracts/market',
    description: 'Token / Oracle / Vesting / 各资金池',
    color: 'warning',
  },
  {
    title: '订单协作',
    path: '/admin/contracts/orders',
    description: 'JointOrder / Asset / ZK / Identity',
    color: 'primary',
  },
]

export default function ContractsOverviewPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">区块链合约</h1>
      <p className="text-text-muted text-sm">Base Sepolia 网络 · 实时链上数据</p>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
        {contractCategories.map(cat => (
          <Link
            key={cat.path}
            to={cat.path}
            className="bg-bg-secondary rounded-xl border border-border-primary p-5 hover:border-border-active transition-all group"
          >
            <div className={`w-10 h-10 rounded-lg bg-${cat.color}/10 flex items-center justify-center mb-3`}>
              <Hexagon className={`w-5 h-5 text-${cat.color}`} />
            </div>
            <h3 className="text-text-primary font-rajdhani font-medium text-sm group-hover:text-primary transition-colors">
              {cat.title}
            </h3>
            <p className="text-text-muted text-xs mt-1 leading-relaxed">{cat.description}</p>
          </Link>
        ))}
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary p-5">
        <h3 className="text-text-primary font-rajdhani font-medium mb-4">29 个已部署合约</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
          {[
            'VIBEToken', 'VIBStaking', 'VIBVesting', 'VIBReserve', 'VIBProtocolFund',
            'VIBInfrastructurePool', 'VIBBuilderReward', 'VIBDevReward', 'VIBIdentity',
            'VIBNodeReward', 'VIBCollaboration', 'VIBDividend', 'AgentRegistry',
            'ZKCredential', 'AssetVault', 'JointOrder', 'PriceOracle', 'VIBOutputReward',
            'VIBEcosystemPool', 'AirdropDistributor', 'CommunityStableFund',
            'LiquidityManager', 'VIBGovernance', 'VIBGovernanceDelegation',
            'VIBContributionPoints', 'VIBVEPoints', 'VIBDispute', 'AgentWallet',
            'EmissionController',
          ].map(name => (
            <div key={name} className="px-3 py-2 bg-bg-tertiary rounded-lg">
              <p className="text-text-primary text-xs font-mono truncate">{name}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
