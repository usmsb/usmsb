// contracts/StakingPage.tsx - 质押合约真实数据
import { useState } from 'react'
import { useStakingStats, useStakingTiers, useStakerInfo } from '../../hooks/useBlockchain'
import StatCard from '../../components/shared/StatCard'
import { useAuthStore } from '@/stores/authStore'
import { Coins, TrendingUp, Users, Shield, Zap } from 'lucide-react'

const TIER_COLORS = ['text-text-muted', 'text-success', 'text-info', 'text-warning', 'text-danger']

export default function StakingPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'tiers' | 'my'>('overview')
  const { data: stats, isLoading } = useStakingStats()
  const { data: tiers, isLoading: tiersLoading } = useStakingTiers()
  const address = useAuthStore(s => s.address)
  const { data: myStake } = useStakerInfo(address || '')

  const tabs = [
    { id: 'overview', label: '总览' },
    { id: 'tiers', label: '等级分布' },
    { id: 'my', label: '我的质押' },
  ] as const

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary font-rajdhani">质押合约</h1>
        <a
          href={`https://sepolia.basescan.org/address/${'0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05'}`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-primary hover:underline"
        >
          Basescan ↗
        </a>
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          title="总质押量 (VIBE)"
          value={stats ? Number(stats.total_staked).toLocaleString(undefined, { maximumFractionDigits: 0 }) : '-'}
          icon={Coins}
          color="primary"
          loading={isLoading}
        />
        <StatCard
          title="奖励池 (VIBE)"
          value={stats ? Number(stats.reward_pool).toLocaleString(undefined, { maximumFractionDigits: 0 }) : '-'}
          icon={Zap}
          color="warning"
          loading={isLoading}
        />
        <StatCard
          title="年化收益率"
          value={stats ? `${stats.apr.toFixed(2)}%` : '-'}
          icon={TrendingUp}
          color={stats && stats.apr > 10 ? 'success' : 'info'}
          loading={isLoading}
        />
        <StatCard
          title="验证者数"
          value={stats?.validator_count ?? '-'}
          icon={Users}
          color="info"
          loading={isLoading}
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border-primary">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-primary text-primary'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
            <h3 className="text-text-primary font-rajdhani font-semibold mb-4">合约参数</h3>
            <div className="space-y-3">
              {[
                ['合约地址', '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05', 'mono'],
                ['奖励率/秒', stats?.reward_rate ?? '-', 'num'],
                ['总质押量', stats ? `${Number(stats.total_staked).toLocaleString()} VIBE` : '-', 'num'],
                ['奖励池余额', stats ? `${Number(stats.reward_pool).toLocaleString()} VIBE` : '-', 'num'],
              ].map(([label, value, type]) => (
                <div key={label as string} className="flex justify-between items-center py-2 border-b border-border-primary/30 last:border-0">
                  <span className="text-text-muted text-sm">{label}</span>
                  <span className={`text-text-primary text-sm font-mono ${type === 'mono' ? 'text-xs' : ''}`}>{value as string}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
            <h3 className="text-text-primary font-rajdhani font-semibold mb-4">质押分布</h3>
            {isLoading ? (
              <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-8 bg-bg-tertiary rounded animate-pulse" />)}</div>
            ) : (
              <div className="space-y-3">
                {(tiers ?? []).map((tier, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span className={`w-8 text-center text-lg font-bold ${TIER_COLORS[i] || 'text-text-muted'}`}>
                      {i + 1}
                    </span>
                    <div className="flex-1">
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-text-primary">{String(tier?.label || `Tier ${i}`)}</span>
                        <span className="text-text-muted font-mono">{tier?.min_stake} VIBE</span>
                      </div>
                      <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${['bg-success', 'bg-info', 'bg-warning', 'bg-danger', 'bg-primary'][i] || 'bg-primary'}`}
                          style={{ width: `${Math.min(100, (1 / (tiers?.length || 1)) * 100 * (Number(tier?.multiplier || 1)))}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-xs text-text-muted font-mono w-16 text-right">
                      ×{tier?.multiplier ?? 1}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tiers Tab */}
      {activeTab === 'tiers' && (
        <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border-primary bg-bg-tertiary">
                <th className="text-left px-4 py-3 text-text-muted font-normal">等级</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">名称</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">最低质押</th>
                <th className="text-left px-4 py-3 text-text-muted font-normal">乘数</th>
              </tr>
            </thead>
            <tbody>
              {tiersLoading ? (
                [...Array(5)].map((_, i) => (
                  <tr key={i} className="border-b border-border-primary/50">
                    {[...Array(4)].map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 w-20 bg-bg-tertiary rounded animate-pulse" /></td>)}
                  </tr>
                ))
              ) : (
                tiers?.map((tier, i) => tier && (
                  <tr key={i} className="border-b border-border-primary/50 hover:bg-bg-tertiary/30">
                    <td className="px-4 py-3">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${TIER_COLORS[i]?.replace('text-', 'bg-').replace('text-', 'text-')}`}>
                        {i + 1}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-text-primary">{tier.label}</td>
                    <td className="px-4 py-3 font-mono text-text-secondary">{Number(tier.min_stake).toLocaleString()} VIBE</td>
                    <td className="px-4 py-3"><span className="text-success font-bold">×{tier.multiplier}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* My Stake Tab */}
      {activeTab === 'my' && (
        <div className="space-y-6">
          {!address ? (
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-12 text-center">
              <Shield className="w-12 h-12 mx-auto text-text-muted mb-3" />
              <p className="text-text-muted">连接钱包查看我的质押信息</p>
            </div>
          ) : myStake ? (
            <div className="grid md:grid-cols-2 gap-6">
              {[
                ['当前质押量', `${Number(myStake.stake).toFixed(2)} VIBE`, 'primary'],
                ['当前等级', `Tier ${myStake.tier}`, 'info'],
                ['待领取奖励', `${Number(myStake.pending_rewards).toFixed(2)} VIBE`, 'warning'],
                ['已领取奖励', `${Number(myStake.rewards_claimed).toFixed(2)} VIBE`, 'success'],
              ].map(([label, value, color]) => (
                <div key={label as string} className="bg-bg-secondary rounded-xl border border-border-primary p-6">
                  <p className="text-text-muted text-sm mb-1">{label}</p>
                  <p className={`text-2xl font-bold font-mono text-${color}`}>{value as string}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-bg-secondary rounded-xl border border-border-primary p-12 text-center">
              <p className="text-text-muted">暂无质押记录</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
