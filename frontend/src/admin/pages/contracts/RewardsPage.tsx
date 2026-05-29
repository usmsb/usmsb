// RewardsPage.tsx - 奖励合约
import { useRewardContracts } from '../../hooks/useBlockchain'
import StatCard from '../../components/shared/StatCard'
import { Gift, Coins, Zap, Users, Code, Server } from 'lucide-react'

const REWARD_CONFIGS = [
  { key: 'VIBBuilderReward', label: 'Builder 奖励', icon: Code, color: 'primary' },
  { key: 'VIBDevReward', label: 'Dev 奖励', icon: Zap, color: 'info' },
  { key: 'VIBNodeReward', label: 'Node 奖励', icon: Server, color: 'warning' },
  { key: 'VIBOutputReward', label: 'Output 奖励', icon: Zap, color: 'success' },
  { key: 'VIBDividend', label: '分红', icon: Gift, color: 'danger' },
]

export default function RewardsPage() {
  const { data: contracts, isLoading } = useRewardContracts()

  const total = contracts?.reduce((sum, c) => sum + Number(c.pool), 0) ?? 0

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">奖励合约</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {REWARD_CONFIGS.map(c => {
          const contract = contracts?.find(x => x.name === c.key)
          return (
            <StatCard
              key={c.key}
              title={c.label}
              value={contract ? `${Number(contract.pool).toLocaleString()}` : '-'}
              icon={c.icon}
              color={c.color as 'primary'}
              loading={isLoading}
            />
          )
        })}
      </div>

      <div className="card hologram overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
              <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">合约</th>
              <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">地址</th>
              <th className="text-right px-4 py-3 text-gray-500 font-cyber font-normal">奖池余额 (VIBE)</th>
              <th className="text-center px-4 py-3 text-gray-500 font-cyber font-normal">状态</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              [...Array(5)].map((_, i) => (
                <tr key={i} className="border-b border-neon-blue/10">
                  {[...Array(4)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>)}
                </tr>
              ))
            ) : (
              contracts?.map(contract => {
                const config = REWARD_CONFIGS.find(c => c.key === contract.name)
                return (
                  <tr key={contract.name} className="border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {config && <config.icon className="w-4 h-4 text-gray-500" />}
                        <span className="text-gray-200 font-medium">{config?.label || contract.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">
                      <a
                        href={`https://sepolia.basescan.org/address/${contract.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-neon-blue"
                      >
                        {contract.address.slice(0, 6)}...{contract.address.slice(-4)}
                      </a>
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-gray-200">
                      {Number(contract.pool).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                        contract.status === 'active' ? 'bg-neon-green/10 text-neon-green border border-neon-green/30' : 'bg-gray-500/10 text-gray-500 border border-gray-500/30'
                      }`}>
                        {contract.status === 'active' ? '● 活跃' : '○ 未知'}
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
