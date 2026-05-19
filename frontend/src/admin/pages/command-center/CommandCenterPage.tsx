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
      <div className="text-4xl font-bold font-mono text-text-primary">
        {time.toLocaleTimeString('zh-CN', { hour12: false })}
      </div>
      <div className="text-text-muted text-sm">
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
    <div className="min-h-screen bg-bg-primary text-text-primary overflow-hidden" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
      {/* 顶部标题栏 */}
      <div className="bg-bg-secondary border-b-2 border-primary px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="w-3 h-3 rounded-full bg-success animate-pulse" />
          <h1 className="text-3xl font-bold tracking-wide text-text-primary">USMSB COMMAND CENTER</h1>
          <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded-full font-mono">v2.0 P3</span>
        </div>
        <ClockDisplay />
      </div>

      {/* 告警滚动条 */}
      {alerts.length > 0 && (
        <div className="bg-danger/10 border-b border-danger/30 px-6 py-1.5 overflow-hidden">
          <div className="animate-marquee whitespace-nowrap text-danger text-sm font-medium">
            {'  •  '.repeat(4)}{alerts.join('  •  ')}{'  •  '.repeat(4)}
          </div>
        </div>
      )}

      {/* 主内容区 4列 */}
      <div className="grid grid-cols-4 gap-3 p-3 h-[calc(100vh-120px)]">

        {/* 左1: Agent 状态 */}
        <div className="bg-bg-secondary rounded-xl border border-border-primary flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-primary/5 flex items-center gap-2">
            <Bot className="w-5 h-5 text-primary" />
            <h2 className="font-bold text-text-primary tracking-wide">AGENT STATUS</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            {/* 数字展示 */}
            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'ONLINE', value: onlineCount, color: 'text-success' },
                { label: 'BUSY', value: busyCount, color: 'text-warning' },
                { label: 'OFFLINE', value: offlineCount, color: 'text-danger' },
              ].map(s => (
                <div key={s.label} className="bg-bg-tertiary rounded-lg p-3 text-center">
                  <div className={`text-3xl font-bold font-mono ${s.color}`}>
                    {dashLoading ? '-' : <AnimatedNumber value={s.value} />}
                  </div>
                  <div className="text-xs text-text-muted mt-1">{s.label}</div>
                </div>
              ))}
            </div>

            {/* 总数 */}
            <div className="bg-bg-tertiary rounded-lg p-3 flex items-center justify-between">
              <span className="text-text-muted text-sm">Agent 总数</span>
              <span className="text-2xl font-bold font-mono text-text-primary">
                {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_agents ?? 0} />}
              </span>
            </div>

            {/* 实时 Agent 列表 */}
            <div className="space-y-1.5">
              <h3 className="text-xs text-text-muted font-semibold uppercase tracking-wider">LIVE FEED</h3>
              {agentList.slice(0, 8).map((agent: Record<string, unknown>) => (
                <div key={agent.agent_id as string} className="flex items-center gap-2 py-1.5 border-b border-border-primary/20">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${agent.status === 'online' ? 'bg-success' : agent.status === 'busy' ? 'bg-warning' : 'bg-danger'}`} />
                  <span className="text-xs font-mono text-text-secondary flex-1 truncate">
                    {String(agent.agent_id).slice(0, 8)}...
                  </span>
                  <span className={`text-xs font-bold uppercase ${
                    agent.status === 'online' ? 'text-success' : agent.status === 'busy' ? 'text-warning' : 'text-danger'
                  }`}>
                    {agent.status as string}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 中左2: 交易流 */}
        <div className="bg-bg-secondary rounded-xl border border-border-primary flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-success/5 flex items-center gap-2">
            <Activity className="w-5 h-5 text-success" />
            <h2 className="font-bold text-text-primary tracking-wide">TRANSACTION FLOW</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-bg-tertiary rounded-lg p-3 text-center">
                <div className="text-2xl font-bold font-mono text-success">
                  {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_transactions ?? 0} />}
                </div>
                <div className="text-xs text-text-muted mt-1">总交易数</div>
              </div>
              <div className="bg-bg-tertiary rounded-lg p-3 text-center">
                <div className="text-2xl font-bold font-mono text-info">
                  {dashLoading ? '-' : <AnimatedNumber value={dashboard?.total_users ?? 0} />}
                </div>
                <div className="text-xs text-text-muted mt-1">总用户</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs text-text-muted font-semibold uppercase tracking-wider">RECENT TXS</h3>
              {recentTxs.slice(0, 10).map((tx: Record<string, unknown>) => (
                <div key={tx.tx_hash as string || String(tx.transaction_id)} className="flex items-center gap-2 py-1.5 border-b border-border-primary/20">
                  <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                    tx.type === 'staking' ? 'bg-primary/10 text-primary' :
                    tx.type === 'reward' ? 'bg-success/10 text-success' :
                    tx.type === 'governance' ? 'bg-warning/10 text-warning' :
                    'bg-info/10 text-info'
                  }`}>
                    {String(tx.type || 'tx').slice(0, 3).toUpperCase()}
                  </span>
                  <span className="text-xs font-mono text-text-secondary flex-1 truncate">
                    {String(tx.tx_hash || tx.transaction_id || '').slice(0, 6)}...
                  </span>
                  <span className="text-xs font-mono text-text-primary">
                    {Number(tx.amount || 0).toFixed(2)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 中右3: 节点健康 */}
        <div className="bg-bg-secondary rounded-xl border border-border-primary flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-info/5 flex items-center gap-2">
            <Server className="w-5 h-5 text-info" />
            <h2 className="font-bold text-text-primary tracking-wide">NODE HEALTH</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            <div className="bg-bg-tertiary rounded-lg p-3 flex items-center justify-between">
              <div className="text-center flex-1">
                <div className="text-3xl font-bold font-mono text-info">
                  {dashLoading ? '-' : onlineNodes}
                </div>
                <div className="text-xs text-text-muted mt-1">在线节点</div>
              </div>
              <div className="w-px h-10 bg-border-primary" />
              <div className="text-center flex-1">
                <div className="text-3xl font-bold font-mono text-text-muted">
                  {dashLoading ? '-' : Math.max(0, (nodes?.total ?? 0) - onlineNodes)}
                </div>
                <div className="text-xs text-text-muted mt-1">离线</div>
              </div>
            </div>

            <div className="space-y-1.5">
              <h3 className="text-xs text-text-muted font-semibold uppercase tracking-wider">NODE LIST</h3>
              {nodeList.slice(0, 10).map((node: Record<string, unknown>) => (
                <div key={node.node_id as string} className="flex items-center gap-2 py-1.5 border-b border-border-primary/20">
                  <Server className={`w-3 h-3 shrink-0 ${node.status === 'online' ? 'text-success' : 'text-danger'}`} />
                  <span className="text-xs font-mono text-text-secondary flex-1 truncate">
                    {String(node.node_id || '').slice(0, 8)}...
                  </span>
                  <span className={`text-xs font-bold ${
                    node.status === 'online' ? 'text-success' : 'text-danger'
                  }`}>
                    {node.status === 'online' ? 'UP' : 'DOWN'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 右4: 系统指标 */}
        <div className="bg-bg-secondary rounded-xl border border-border-primary flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-warning/5 flex items-center gap-2">
            <Zap className="w-5 h-5 text-warning" />
            <h2 className="font-bold text-text-primary tracking-wide">SYSTEM METRICS</h2>
          </div>
          <div className="p-4 flex-1 space-y-4 overflow-auto">
            {[
              { label: '总交易额', value: dashboard?.total_transaction_volume ?? 0, unit: 'VIBE', icon: Zap, color: 'text-warning' },
              { label: 'TVL', value: dashboard?.total_volume_24h ?? 0, unit: 'USD', icon: Globe, color: 'text-info' },
              { label: '活跃订单', value: dashboard?.pending_orders ?? 0, unit: '单', icon: Activity, color: 'text-success' },
              { label: '交易笔数', value: dashboard?.tx_count_24h ?? 0, unit: '笔', icon: TrendingUp, color: 'text-primary' },
            ].map(m => (
              <div key={m.label} className="bg-bg-tertiary rounded-lg p-3">
                <div className="flex items-center gap-2 mb-2">
                  <m.icon className={`w-4 h-4 ${m.color}`} />
                  <span className="text-text-muted text-xs">{m.label}</span>
                </div>
                <div className="flex items-baseline gap-1">
                  <span className={`text-2xl font-bold font-mono ${m.color}`}>
                    {dashLoading ? '-' : <AnimatedNumber value={m.value} />}
                  </span>
                  <span className="text-text-muted text-xs">{m.unit}</span>
                </div>
              </div>
            ))}

            {/* 匹配效率 */}
            <div className="bg-bg-tertiary rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-4 h-4 text-primary" />
                <span className="text-text-muted text-xs">匹配效率</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-bg-primary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full" style={{ width: '78%' }} />
                </div>
                <span className="text-primary font-bold text-sm">78%</span>
              </div>
            </div>

            {/* 在线人数 */}
            <div className="bg-bg-tertiary rounded-lg p-3 flex items-center justify-between">
              <span className="text-text-muted text-xs">WebSocket 在线</span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
                <span className="text-success font-bold font-mono">{onlineCount + 1}</span>
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
