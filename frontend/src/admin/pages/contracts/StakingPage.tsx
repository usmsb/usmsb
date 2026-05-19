/** StakingPage - 质押生态 */
import { useState } from 'react'
import { Coins } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

export default function StakingPage() {
  const [walletInput, setWalletInput] = useState('')
  const [queryAddress, setQueryAddress] = useState('')

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">质押生态</h1>
      <p className="text-text-muted text-sm">VIBStaking · Dividend · VEPoints · EmissionController</p>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard title="总质押量" value="-" icon={Coins} color="primary" />
        <StatCard title="当前 APY" value="-" icon={Coins} color="success" suffix="%" />
        <StatCard title="Staker 数" value="-" icon={Coins} color="info" />
        <StatCard title="累计奖励" value="-" icon={Coins} color="warning" suffix="VIBE" />
        <StatCard title="待分配红利" value="-" icon={Coins} color="warning" suffix="VIBE" />
        <StatCard title="VIBE 价格" value="-" icon={Coins} color="primary" prefix="$" />
      </div>

      {/* Tab: 质押概览 | 奖励追踪 | 等级分布 */}
      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="flex border-b border-border-primary">
          {['质押概览', '奖励追踪', '等级分布', '历史走势'].map((tab, i) => (
            <button key={tab}
              className={`px-6 py-3 text-sm font-rajdhani font-medium transition-colors
                ${i === 0 ? 'text-primary border-b-2 border-primary' : 'text-text-muted hover:text-text-secondary'}`}>
              {tab}
            </button>
          ))}
        </div>

        <div className="p-6 space-y-6">
          {/* 质押概览内容 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="text-text-primary font-rajdhani font-medium">实时指标</h4>
              {[
                { label: '当前 APY', value: '-%', sub: '动态调整范围: 3%~10%' },
                { label: '基础 APY', value: '-%' },
                { label: '总质押量', value: '- VIBE' },
                { label: 'Staker 数量', value: '-' },
                { label: '累计发放奖励', value: '- VIBE' },
              ].map(item => (
                <div key={item.label} className="flex justify-between items-center py-2 border-b border-border-primary">
                  <span className="text-text-muted text-sm">{item.label}</span>
                  <div className="text-right">
                    <span className="text-text-primary font-mono">{item.value}</span>
                    {item.sub && <p className="text-text-muted text-xs">{item.sub}</p>}
                  </div>
                </div>
              ))}
            </div>

            <div className="space-y-4">
              <h4 className="text-text-primary font-rajdhani font-medium">奖励追踪</h4>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={walletInput}
                  onChange={e => setWalletInput(e.target.value)}
                  placeholder="输入钱包地址查询..."
                  className="flex-1 bg-bg-tertiary text-text-primary rounded-lg px-4 py-2 border border-border-primary focus:border-primary outline-none text-sm"
                />
                <button
                  onClick={() => setQueryAddress(walletInput)}
                  className="px-4 py-2 bg-primary text-white rounded-lg text-sm hover:bg-primary-hover transition-colors"
                >
                  查询
                </button>
              </div>
              {queryAddress ? (
                <div className="p-4 bg-bg-tertiary rounded-lg space-y-2 text-sm">
                  <p className="text-text-muted">查询结果: <span className="text-text-primary font-mono">{queryAddress.slice(0, 10)}...</span></p>
                  <p className="text-text-secondary">（链上数据将通过 Multicall3 批量读取）</p>
                </div>
              ) : (
                <p className="text-text-muted text-sm">输入钱包地址查询质押信息</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
