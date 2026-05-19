// AgentDetailDrawer.tsx - Agent 详情抽屉
import { X, ExternalLink } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import VIBEAmount from '../shared/VIBEAmount'
import AddressDisplay from '../shared/AddressDisplay'
import { Brain, Coins, TrendingUp, Shield, Clock } from 'lucide-react'

interface AgentDetailDrawerProps {
  agent: {
    agent_id: string
    name?: string
    agent_type?: string
    status: string
    stake: number
    balance?: number
    reputation?: number
    capabilities?: string[]
    created_at?: number
    last_active?: number
    node_id?: string
    wallet_address?: string
  } | null
  isOpen: boolean
  onClose: () => void
}

export default function AgentDetailDrawer({ agent, isOpen, onClose }: AgentDetailDrawerProps) {
  if (!isOpen || !agent) return null

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-bg-secondary border-l border-border-primary shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text-primary font-rajdhani">
                {agent.name || 'Agent 详情'}
              </h2>
              <p className="text-xs text-text-muted font-mono">
                {agent.agent_id.slice(0, 12)}...
              </p>
            </div>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* 基本状态 */}
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-bg-tertiary rounded-xl p-4">
              <p className="text-text-muted text-xs mb-1">状态</p>
              <StatusBadge status={agent.status} />
            </div>
            <div className="bg-bg-tertiary rounded-xl p-4">
              <p className="text-text-muted text-xs mb-1">类型</p>
              <p className="text-text-primary text-sm">{agent.agent_type || 'ai_agent'}</p>
            </div>
          </div>

          {/* 质押信息 */}
          <div className="space-y-3">
            <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
              <Coins className="w-4 h-4" /> 财务信息
            </h3>
            <div className="space-y-2">
              {[
                ['质押量', <VIBEAmount key="stake" value={agent.stake} />],
                ['余额', <VIBEAmount key="balance" value={agent.balance ?? 0} />],
                ['信誉分', `${((agent.reputation ?? 0) * 100).toFixed(1)}%`],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between items-center py-2 border-b border-border-primary/30 last:border-0">
                  <span className="text-text-muted text-sm">{label}</span>
                  <span className="text-text-primary text-sm font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 链上信息 */}
          {agent.wallet_address && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
                <Shield className="w-4 h-4" /> 钱包地址
              </h3>
              <AddressDisplay address={agent.wallet_address} explorer="https://sepolia.basescan.org/address/" />
            </div>
          )}

          {/* 时间信息 */}
          <div className="space-y-3">
            <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
              <Clock className="w-4 h-4" /> 时间信息
            </h3>
            <div className="space-y-2">
              {[
                ['创建时间', agent.created_at ? new Date(agent.created_at * 1000).toLocaleString('zh-CN') : '-'],
                ['最后活动', agent.last_active ? new Date(agent.last_active * 1000).toLocaleString('zh-CN') : '-'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between items-center py-2 border-b border-border-primary/30 last:border-0">
                  <span className="text-text-muted text-sm">{label}</span>
                  <span className="text-text-primary text-sm">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 能力标签 */}
          {agent.capabilities && agent.capabilities.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
                <TrendingUp className="w-4 h-4" /> 能力
              </h3>
              <div className="flex flex-wrap gap-2">
                {agent.capabilities.map((cap, i) => (
                  <span key={i} className="px-2.5 py-1 bg-primary/10 text-primary text-xs rounded-full">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* 区块浏览器链接 */}
          {agent.wallet_address && (
            <a
              href={`https://sepolia.basescan.org/address/${agent.wallet_address}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-primary hover:underline text-sm"
            >
              <ExternalLink className="w-4 h-4" /> 在 Basescan 查看
            </a>
          )}
        </div>
      </div>
    </>
  )
}
