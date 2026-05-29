// CommandCenterPage.tsx - 指挥中心大屏幕
import { useQuery } from '@tanstack/react-query'
import { fetchDashboard, fetchAgents, fetchTransactions, fetchNodes } from '../../api/adminApi'
import type { DashboardData, AgentListData, TransactionListData, NodeListData } from '../../api/adminApi'
import { Bot, Activity, Zap, Server, TrendingUp, Globe, Clock, AlertTriangle } from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

// 实时时钟
function ClockDisplay() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <div className="text-right">
      <div className="text-4xl font-bold font-mono text-neon-blue" style={{ textShadow: '0 0 20px rgba(0, 245, 255, 0.5)' }}>
        {time.toLocaleTimeString('zh-CN', { hour12: false })}
      </div>
      <div className="text-gray-500 text-sm font-cyber">
        {time.toLocaleDateString('zh-CN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
      </div>
    </div>
  )
}

// 数字滚动动画
function AnimatedNumber({ value, duration = 1000 }: { value: number; duration?: number }) {
  const [display, setDisplay] = useState(0)
  const prevRef = useRef(0)

  useEffect(() => {
    const start = prevRef.current
    const end = value
    const startTime = performance.now()

    const animate = (now: number) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(start + (end - start) * eased))
      if (progress < 1) requestAnimationFrame(animate)
      else prevRef.current = end
    }
    requestAnimationFrame(animate)
  }, [value, duration])

  return <span>{display.toLocaleString()}</span>
}

export default function CommandCenterPage() {
  const { data: dashboard, isLoading: dashLoading } = useQuery<DashboardData>({
    queryKey: ['admin', 'dashboard'],
    queryFn: fetchDashboard,
    refetchInterval: 15000,
  })
  const { data: agents, isLoading: agentsLoading } = useQuery<AgentListData>({
    queryKey: ['admin', 'agents', 1],
    queryFn: () => fetchAgents({ page: 1, page_size: 100 }),
    refetchInterval: 15000,
  })
  const { data: transactions } = useQuery<TransactionListData>({
    queryKey: ['admin', 'transactions', 1],
    queryFn: () => fetchTransactions({ page: 1, page_size: 50 }),
    refetchInterval: 30000,
  })
  const { data: nodes } = useQuery<NodeListData>({
    queryKey: ['admin', 'nodes', 1],
    queryFn: () => fetchNodes(),
    refetchInterval: 15000,
  })

  const agentList = agents?.agents ?? []
  const onlineCount = agentList.filter((a: Record<string, unknown>) => a.status === 'online').length
  const busyCount = agentList.filter((a: Record<string, unknown>) => a.status === 'busy').length
  const offlineCount = agentList.filter((a: Record<string, unknown>) => a.status === 'offline').length
  const recentTxs = transactions?.transactions ?? []
  const nodeList = nodes?.nodes ?? []
  const onlineNodes = nodeList.filter((n: Record<string, unknown>) => n.status === 'online').length

  // 告警滚动
  const alerts = [
    '系统运行正常',
    onlineCount === 0 ? '⚠️ 无在线 Agent' : '',
    onlineNodes < 3 ? '⚠️ 在线节点数偏低' : '',
    'USMSB v2.0 P3 运行中',
  ].filter(Boolean)

  return (
    <div className="bg-cyber-dark text-gray-200 overflow-hidden font-cyber -m-6 pt-16">
      {/* 顶部标题栏 - 紧凑版 */}
      <div className="bg-cyber-card border-b border-neon-blue/30 px-6 py-2 flex items-center justify-between" style={{ boxShadow: '0 0 15px rgba(0, 245, 255, 0.15)' }}>
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-neon-green animate-pulse" style={{ boxShadow: '0 0 8px #00ff88' }} />
          <h1 className="text-xl font-bold tracking-wide text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple">
            USMSB COMMAND CENTER
          </h1>
          <span className="text-xs bg-neon-blue/10 text-neon-blue px-2 py-0.5 rounded-full font-mono border border-neon-blue/30">v2.0 P3</span>
        </div>
        <ClockDisplay />
      </div>

      {/* 告警滚动条 */}
      {alerts.length > 0 && (
        <div className="bg-danger/10 border-b border-danger/30 px-6 py-1 overflow-hidden">
          <div className="animate-marquee whitespace-nowrap text-danger text-xs font-medium">
            {'  •  '.repeat(4)}{alerts.join('  •  ')}{'  •  '.repeat(4)}
          </div>
        </div>
      )}

      {/* 主内容区 4列 - 减去顶部标题和告警栏的高度 */}
      <div className="grid grid-cols-4 gap-3 p-3 h-[calc(100vh-64px-48px-48px)]">

        {/* 左1: Agent 状态 */}
        <div className="bg-cyber-card rounded-xl border border-neon-blue/30 flex flex-col overflow-hidden" style={{ boxShadow: '0 0 20px rgba(0, 245, 255, 0.1)' }}>
          <div className="px-4 py-3 border-b border-neon-blue/20 bg-neon-blue/5 flex items-center gap-2">
            <Bot className="w-5 h-5 text-neon-blue" />
            <h2 className="font-bold text-neon-blue tracking-wide font-cyber">AGENT STATUS</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            {/* 数字展示 */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'ONLINE', value: onlineCount, color: 'text-neon-green' },
                { label: 'BUSY', value: busyCount, color: 'text-neon-yellow' },
                { label: 'OFFLINE', value: offlineCount, color: 'text-neon-red' },
              ].map(s => (
                <div key={s.label} className="bg-cyber-dark rounded-lg p-3 text-center border border-neon-blue/20">
                  <div className={`text-3xl font-bold font-mono ${s.color}`} style={{ textShadow: `0 0 10px currentColor` }}>
                    {dashLoading ? '-' : <AnimatedNumber value={s.value} />}
                  </div>
                  <div className="text-xs text-gray-500 mt-1 font-cyber">{s.label}</div>
                </div>
              ))}
            </div>

            {/* 总数 */}
            <div className="bg-cyber-dark rounded-lg p-3 flex items-center justify-between border border-neon-blue/20">
              <span className="text-gray-500 text-sm font-cyber">Agent 总数</span>
              <span className="text-2xl font-bold font-mono text-neon-blue" style={{ textShadow: '0 0 10px rgba(0, 245, 255, 0.5)' }}>
                {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_agents ?? 0} />}
              </span>
            </div>

            {/* 实时 Agent 列表 */}
            <div className="space-y-1.5">
              <h3 className="text-xs text-gray-500 font-semibold uppercase tracking-wider font-cyber">LIVE FEED</h3>
              {agentList.slice(0, 8).map((agent: Record<string, unknown>) => (
                <div key={agent.agent_id as string} className="flex items-center gap-2 py-1.5 border-b border-neon-blue/10">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${agent.status === 'online' ? 'bg-neon-green' : agent.status === 'busy' ? 'bg-neon-yellow' : 'bg-neon-red'}`}
                    style={{ boxShadow: agent.status === 'online' ? '0 0 5px #00ff88' : agent.status === 'busy' ? '0 0 5px #ffff00' : '0 0 5px #ff0040' }}
                  />
                  <span className="text-xs font-mono text-gray-400 flex-1 truncate">
                    {String(agent.agent_id).slice(0, 8)}...
                  </span>
                  <span className={`text-xs font-bold uppercase font-cyber ${
                    agent.status === 'online' ? 'text-neon-green' : agent.status === 'busy' ? 'text-neon-yellow' : 'text-neon-red'
                  }`}>
                    {agent.status as string}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 中左2: 交易流 */}
        <div className="bg-cyber-card rounded-xl border border-neon-purple/30 flex flex-col overflow-hidden" style={{ boxShadow: '0 0 20px rgba(191, 0, 255, 0.1)' }}>
          <div className="px-4 py-3 border-b border-neon-purple/20 bg-neon-purple/5 flex items-center gap-2">
            <Activity className="w-5 h-5 text-neon-purple" />
            <h2 className="font-bold text-neon-purple tracking-wide font-cyber">TRANSACTION FLOW</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-cyber-dark rounded-lg p-3 text-center border border-neon-purple/20">
                <div className="text-2xl font-bold font-mono text-neon-green" style={{ textShadow: '0 0 10px #00ff88' }}>
                  {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_transactions ?? 0} />}
                </div>
                <div className="text-xs text-gray-500 mt-1 font-cyber">总交易数</div>
              </div>
              <div className="bg-cyber-dark rounded-lg p-3 text-center border border-neon-purple/20">
                <div className="text-2xl font-bold font-mono text-neon-purple" style={{ textShadow: '0 0 10px #bf00ff' }}>
                  {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_users ?? 0} />}
                </div>
                <div className="text-xs text-gray-500 mt-1 font-cyber">总用户</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs text-gray-500 font-semibold uppercase tracking-wider font-cyber">RECENT TXS</h3>
              {recentTxs.slice(0, 10).map((tx: Record<string, unknown>) => (
                <div key={tx.tx_hash as string || String(tx.transaction_id)} className="flex items-center gap-2 py-1.5 border-b border-neon-purple/10">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded font-cyber ${
                    tx.type === 'staking' ? 'bg-neon-blue/10 text-neon-blue' :
                    tx.type === 'reward' ? 'bg-neon-green/10 text-neon-green' :
                    tx.type === 'governance' ? 'bg-neon-yellow/10 text-neon-yellow' :
                    'bg-neon-purple/10 text-neon-purple'
                  }`}>
                    {String(tx.type || 'tx').slice(0, 3).toUpperCase()}
                  </span>
                  <span className="text-xs font-mono text-gray-400 flex-1 truncate">
                    {String(tx.tx_hash || tx.transaction_id || '').slice(0, 6)}...
                  </span>
                  <span className="text-xs font-mono text-gray-200">
                    {Number(tx.amount || 0).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 中右3: 节点健康 */}
        <div className="bg-cyber-card rounded-xl border border-neon-blue/30 flex flex-col overflow-hidden" style={{ boxShadow: '0 0 20px rgba(0, 245, 255, 0.1)' }}>
          <div className="px-4 py-3 border-b border-neon-blue/20 bg-neon-blue/5 flex items-center gap-2">
            <Server className="w-5 h-5 text-neon-blue" />
            <h2 className="font-bold text-neon-blue tracking-wide font-cyber">NODE HEALTH</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            <div className="bg-cyber-dark rounded-lg p-3 flex items-center justify-between border border-neon-blue/20">
              <div className="text-center flex-1">
                <div className="text-3xl font-bold font-mono text-neon-blue" style={{ textShadow: '0 0 10px rgba(0, 245, 255, 0.5)' }}>
                  {dashLoading ? '-' : onlineNodes}
                </div>
                <div className="text-xs text-gray-500 mt-1 font-cyber">在线节点</div>
              </div>
              <div className="w-px h-10 bg-neon-blue/30" />
              <div className="text-center flex-1">
                <div className="text-3xl font-bold font-mono text-gray-500">
                  {dashLoading ? '-' : Math.max(0, (nodes?.total ?? 0) - onlineNodes)}
                </div>
                <div className="text-xs text-gray-500 mt-1 font-cyber">离线</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs text-gray-500 font-semibold uppercase tracking-wider font-cyber">NODE LIST</h3>
              {nodeList.slice(0, 10).map((node: Record<string, unknown>) => (
                <div key={node.node_id as string} className="flex items-center gap-2 py-1.5 border-b border-neon-blue/10">
                  <Server className={`w-3 h-3 shrink-0 ${node.status === 'online' ? 'text-neon-green' : 'text-neon-red'}`}
                    style={node.status === 'online' ? { filter: 'drop-shadow(0 0 5px #00ff88)' } : { filter: 'drop-shadow(0 0 5px #ff0040)' }}
                  />
                  <span className="text-xs font-mono text-gray-400 flex-1 truncate">
                    {String(node.node_id || '').slice(0, 8)}...
                  </span>
                  <span className={`text-xs font-bold font-cyber ${
                    node.status === 'online' ? 'text-neon-green' : 'text-neon-red'
                  }`}>
                    {node.status === 'online' ? 'UP' : 'DOWN'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 右4: 系统指标 */}
        <div className="bg-cyber-card rounded-xl border border-neon-yellow/30 flex flex-col overflow-hidden" style={{ boxShadow: '0 0 20px rgba(255, 255, 0, 0.1)' }}>
          <div className="px-4 py-3 border-b border-neon-yellow/20 bg-neon-yellow/5 flex items-center gap-2">
            <Zap className="w-5 h-5 text-neon-yellow" />
            <h2 className="font-bold text-neon-yellow tracking-wide font-cyber">SYSTEM METRICS</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            {[
              { label: '总交易额', value: dashboard?.total_transaction_volume ?? 0, unit: 'VIBE', icon: Zap, color: 'text-neon-yellow' },
              { label: 'TVL', value: dashboard?.total_volume_24h ?? 0, unit: 'USD', icon: Globe, color: 'text-neon-purple' },
              { label: '活跃订单', value: dashboard?.pending_orders ?? 0, unit: '单', icon: Activity, color: 'text-neon-green' },
              { label: '交易笔数', value: dashboard?.tx_count_24h ?? 0, unit: '笔', icon: TrendingUp, color: 'text-neon-blue' },
            ].map(m => (
              <div key={m.label} className="bg-cyber-dark rounded-lg p-3 border border-neon-yellow/20">
                <div className="flex items-center gap-2 mb-2">
                  <m.icon className={`w-4 h-4 ${m.color}`} />
                  <span className="text-gray-500 text-xs font-cyber">{m.label}</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className={`text-2xl font-bold font-mono ${m.color}`} style={{ textShadow: `0 0 10px currentColor` }}>
                    {dashLoading ? '-' : <AnimatedNumber value={m.value} />}
                  </span>
                  <span className="text-gray-500 text-xs font-cyber">{m.unit}</span>
                </div>
              </div>
            ))}

            {/* 匹配效率 */}
            <div className="bg-cyber-dark rounded-lg p-3 border border-neon-yellow/20">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-neon-yellow" />
                <span className="text-gray-500 text-xs font-cyber">匹配效率</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-cyber-dark rounded-full overflow-hidden border border-neon-yellow/20">
                  <div className="h-full bg-neon-yellow rounded-full" style={{ width: '78%', boxShadow: '0 0 10px #ffff00' }} />
                </div>
                <span className="text-neon-yellow font-bold text-sm font-cyber">78%</span>
              </div>
            </div>

            {/* 在线人数 */}
            <div className="bg-cyber-dark rounded-lg p-3 flex items-center justify-between border border-neon-green/20">
              <span className="text-gray-500 text-xs font-cyber">WebSocket 在线</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" style={{ boxShadow: '0 0 10px #00ff88' }} />
                <span className="text-neon-green font-bold font-mono">{onlineCount + 1}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes marquee {
          0% { transform: translateX(100%); }
          100% { transform: translateX(-100%); }
        }
        .animate-marquee {
          animation: marquee 20s linear infinite;
        }
      `}</style>
    </div>
  )
}
