/**
 * LiveFeed - 实时动态面板
 */
import { useState } from 'react'
import StatusBadge from '../../../components/shared/StatusBadge'
import type { AgentListData, TransactionListData } from '../../../api/adminApi'

interface LiveFeedProps {
  agents: AgentListData['agents']
  transactions: TransactionListData['transactions']
}

type Tab = 'agents' | 'transactions'

function timeAgo(timestamp: number): string {
  const seconds = Math.floor(Date.now() / 1000 - timestamp)
  if (seconds < 60) return `${seconds}s前`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m前`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h前`
  return `${Math.floor(seconds / 86400)}d前`
}

function shortAddr(addr: string): string {
  if (!addr || addr.length < 12) return addr || '-'
  return `${addr.slice(0, 6)}...${addr.slice(-4)}`
}

export default function LiveFeed({ agents, transactions }: LiveFeedProps) {
  const [activeTab, setActiveTab] = useState<Tab>('agents')

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-neon-blue/20">
        {[
          { key: 'agents', label: 'Agent' },
          { key: 'transactions', label: '交易' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as Tab)}
            className={`flex-1 py-3 text-sm font-cyber font-medium transition-colors
              ${activeTab === tab.key
                ? 'text-neon-blue border-b-2 border-neon-blue'
                : 'text-gray-500 hover:text-gray-300'}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="px-4 py-2 border-b border-neon-blue/20 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse"
          style={{ boxShadow: '0 0 10px #00ff88' }} />
        <span className="text-gray-500 text-xs">实时更新中</span>
      </div>

      <div className="flex-1 overflow-auto p-3 space-y-2">
        {activeTab === 'agents' ? (
          agents.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-8">暂无 Agent 数据</p>
          ) : (
            agents.map(agent => (
              <div key={agent.agent_id}
                className="flex items-center gap-3 p-2.5 rounded-lg bg-cyber-dark/50 hover:bg-cyber-card transition-colors">
                <div className="w-8 h-8 rounded-lg bg-neon-blue/10 border border-neon-blue/30 flex items-center justify-center shrink-0">
                  <span className="text-neon-blue text-xs font-bold">🤖</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-200 text-sm font-medium truncate">
                    {agent.name || agent.agent_id.slice(0, 12)}
                  </p>
                  <p className="text-gray-500 text-xs">
                    {agent.last_heartbeat ? timeAgo(agent.last_heartbeat) : '-'}
                  </p>
                </div>
                <StatusBadge status={agent.status} size="sm" />
              </div>
            ))
          )
        ) : (
          transactions.length === 0 ? (
            <p className="text-center text-gray-500 text-sm py-8">暂无交易数据</p>
          ) : (
            transactions.map(tx => (
              <div key={tx.tx_id}
                className="flex items-center gap-3 p-2.5 rounded-lg bg-cyber-dark/50 hover:bg-cyber-card transition-colors">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0
                  ${tx.status === 'completed' ? 'bg-neon-green/10 border border-neon-green/30' : 'bg-neon-yellow/10 border border-neon-yellow/30'}`}>
                  <span className={tx.status === 'completed' ? 'text-neon-green' : 'text-neon-yellow'}>💰</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-gray-200 text-sm truncate">
                    {shortAddr(tx.from_address || tx.tx_id)}
                  </p>
                  <p className="text-gray-500 text-xs">
                    {tx.created_at ? timeAgo(tx.created_at) : '-'}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <p className={`text-sm font-mono ${tx.from_address ? 'text-neon-red' : 'text-neon-green'}`}>
                    {tx.amount.toFixed(2)}
                  </p>
                  <StatusBadge status={tx.status} size="sm" />
                </div>
              </div>
            ))
          )
        )}
      </div>

      <div className="p-3 border-t border-neon-blue/20">
        <a href={activeTab === 'agents' ? '/admin/agents' : '/admin/transactions'}
          className="block text-center text-neon-blue text-sm hover:underline">
          查看全部 →
        </a>
      </div>
    </div>
  )
}
