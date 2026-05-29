// MarketPage.tsx - 市场数据（预言机 + Vesting + 资金池）
import { useTokenBalance, useStakingStats } from '../../hooks/useBlockchain'
import { useAuthStore } from '@/stores/authStore'
import StatCard from '../../components/shared/StatCard'
import { useState } from 'react'
import { ExternalLink, Coins, Globe, Lock } from 'lucide-react'

const MARKET_CONTRACTS = [
  { name: 'VIBEToken', label: 'VIBE Token', addr: '0x93C52dF000317e12F891474B46d8B05652430bDC' },
  { name: 'PriceOracle', label: '价格预言机', addr: '0x20306509a6b2f0b56ad55C193b4505CA5E62bc48' },
  { name: 'VIBVesting', label: 'Vesting', addr: '0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924' },
  { name: 'VIBReserve', label: '储备金', addr: '0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263' },
  { name: 'VIBProtocolFund', label: '协议基金', addr: '0x0F39011e7E542D939C1dce40754a86b01BB3fA5a' },
  { name: 'VIBEcosystemPool', label: '生态池', addr: '0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06' },
]

export default function MarketPage() {
  const address = useAuthStore(s => s.address)
  const { data: tokenData, isLoading } = useTokenBalance(address || '')
  const [activeTab, setActiveTab] = useState<'overview' | 'vesting'>('overview')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">市场数据</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="我的 VIBE 余额"
          value={tokenData ? `${Number(tokenData.balance).toFixed(2)}` : '-'}
          icon={Coins}
          color="primary"
          loading={isLoading}
        />
        <StatCard
          title="总供应量"
          value={tokenData ? `${Number(tokenData.total_supply).toLocaleString()}` : '-'}
          icon={Coins}
          color="info"
          loading={isLoading}
        />
        <StatCard title="预言机价格" value="-" icon={Globe} color="warning" loading={false} />
        <StatCard title="流动性" value="-" icon={Coins} color="success" loading={false} />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-neon-blue/20">
        {(['overview', 'vesting'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors font-cyber ${
              activeTab === tab ? 'border-neon-blue text-neon-blue' : 'border-transparent text-gray-500 hover:text-neon-blue'
            }`}
          >
            {tab === 'overview' ? '合约列表' : 'Vesting 详情'}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <div className="card hologram overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-neon-blue/20 bg-cyber-dark/50">
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">名称</th>
                <th className="text-left px-4 py-3 text-gray-500 font-cyber font-normal">合约地址</th>
                <th className="text-right px-4 py-3 text-gray-500 font-cyber font-normal">操作</th>
              </tr>
            </thead>
            <tbody>
              {MARKET_CONTRACTS.map(c => (
                <tr key={c.name} className="border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                  <td className="px-4 py-3 text-gray-200 font-medium">{c.label}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.addr}</td>
                  <td className="px-4 py-3 text-right">
                    <a
                      href={`https://sepolia.basescan.org/address/${c.addr}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-neon-blue hover:underline text-xs font-cyber"
                    >
                      <ExternalLink className="w-3 h-3" /> 查看
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'vesting' && (
        <div className="card hologram p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-neon-blue font-cyber font-semibold">Vesting 合约</h3>
            <a
              href="https://sepolia.basescan.org/address/0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-neon-blue hover:underline font-cyber"
            >
              Basescan ↗
            </a>
          </div>
          <div className="space-y-3">
            {[
              ['管理员', '0xAbCdEf0000000000000000000000000000000000'],
              ['部署时间', '~2026-03'],
              ['锁仓类型', 'TGE + 12个月线性释放'],
              ['受益人数', '待查询'],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between py-2 border-b border-neon-blue/10 last:border-0">
                <span className="text-gray-500 text-sm font-cyber">{label}</span>
                <span className="text-gray-200 text-sm font-mono">{value}</span>
              </div>
            ))}
          </div>
          <p className="text-gray-500 text-xs mt-4 font-cyber">
            Vesting 数据需要连接钱包后通过合约读取。部署时间基于项目早期区块估算。
          </p>
        </div>
      )}
    </div>
  )
}
