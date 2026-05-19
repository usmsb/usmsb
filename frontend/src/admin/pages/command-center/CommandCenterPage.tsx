/**
 * CommandCenterPage - 大屏幕指挥调度模式
 * 独立全屏路由，无 Sidebar/Header
 */
import { useState, useEffect } from 'react'
import { Monitor, RefreshCw, Maximize2, Minimize2, Pause, Settings, Bell, AlertTriangle } from 'lucide-react'
import clsx from 'clsx'

// Panel 组件
function Panel({ title, children, alert }: { title: string; children: React.ReactNode; alert?: boolean }) {
  return (
    <div className={clsx(
      'bg-bg-secondary rounded-2xl border p-6 h-full flex flex-col',
      alert ? 'border-danger/50 animate-pulse' : 'border-border-primary'
    )}>
      <h2 className="font-orbitron text-lg text-text-primary mb-4">{title}</h2>
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}

// Panel 1: Agent 状态
function AgentStatusPanel() {
  return (
    <Panel title="实时 Agent 状态">
      <div className="flex flex-col items-center justify-center h-full space-y-4">
        {/* 模拟数字 */}
        <div className="text-center">
          <p className="text-text-muted text-sm">总 Agent</p>
          <p className="font-orbitron text-6xl font-bold text-text-primary">1,234</p>
        </div>
        <div className="grid grid-cols-3 gap-6 text-center w-full px-4">
          <div>
            <p className="text-success text-2xl font-orbitron font-bold">892</p>
            <p className="text-text-muted text-xs mt-1">🟢 在线</p>
          </div>
          <div>
            <p className="text-warning text-2xl font-orbitron font-bold">156</p>
            <p className="text-text-muted text-xs mt-1">🟡 忙碌</p>
          </div>
          <div>
            <p className="text-danger text-2xl font-orbitron font-bold">186</p>
            <p className="text-text-muted text-xs mt-1">🔴 离线</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-4 w-full px-4 text-center">
          <div className="p-3 bg-bg-tertiary rounded-lg">
            <p className="text-text-muted text-xs">今日新增</p>
            <p className="text-success font-orbitron">+23</p>
          </div>
          <div className="p-3 bg-bg-tertiary rounded-lg">
            <p className="text-text-muted text-xs">在线率</p>
            <p className="text-success font-orbitron">72.3%</p>
          </div>
        </div>
      </div>
    </Panel>
  )
}

// Panel 2: 交易状态
function TransactionPanel() {
  return (
    <Panel title="全局交易状态">
      <div className="space-y-4">
        <div className="text-center">
          <p className="text-text-muted text-sm">今日交易金额</p>
          <p className="font-orbitron text-4xl font-bold text-success">¥ 234,567</p>
          <p className="text-success text-sm">↑ 18.3%</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="text-center p-3 bg-bg-tertiary rounded-lg">
            <p className="text-text-muted text-xs">交易笔数</p>
            <p className="font-orbitron text-2xl text-primary">1,234</p>
          </div>
          <div className="text-center p-3 bg-bg-tertiary rounded-lg">
            <p className="text-text-muted text-xs">成功率</p>
            <p className="font-orbitron text-2xl text-success">95.3%</p>
          </div>
        </div>
        <div className="p-3 bg-bg-tertiary rounded-lg text-center">
          <p className="text-text-muted text-xs mb-2">24小时交易额</p>
          <div className="flex items-end gap-1 h-12 justify-center">
            {Array.from({ length: 24 }, (_, i) => (
              <div key={i} className="w-3 bg-primary rounded-t"
                style={{ height: `${Math.random() * 80 + 20}%` }} />
            ))}
          </div>
        </div>
      </div>
    </Panel>
  )
}

// Panel 3: 匹配效率
function MatchingPanel() {
  const funnel = [
    { label: '发布需求', value: 342, pct: '100%' },
    { label: 'AI推荐', value: 289, pct: '84.5%' },
    { label: '发起协商', value: 156, pct: '45.6%' },
    { label: '达成合作', value: 89, pct: '26.0%' },
    { label: '成功交付', value: 67, pct: '19.6%' },
  ]

  return (
    <Panel title="匹配效率实时看板">
      <div className="space-y-2">
        {funnel.map((item, i) => (
          <div key={item.label} className="relative">
            <div className="flex justify-between mb-1">
              <span className="text-text-secondary text-sm">{item.label}</span>
              <span className="text-text-muted text-xs">{item.pct}</span>
            </div>
            <div className="h-6 bg-bg-tertiary rounded overflow-hidden">
              <div className="h-full bg-success rounded transition-all"
                style={{ width: `${item.pct}` }} />
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-2 mt-4">
        <div className="text-center p-2 bg-bg-tertiary rounded">
          <p className="text-text-muted text-xs">匹配时长</p>
          <p className="text-text-primary font-mono text-sm">2h 34m</p>
        </div>
        <div className="text-center p-2 bg-bg-tertiary rounded">
          <p className="text-text-muted text-xs">协商轮数</p>
          <p className="text-text-primary font-mono text-sm">3.2</p>
        </div>
        <div className="text-center p-2 bg-bg-tertiary rounded">
          <p className="text-text-muted text-xs">达成率</p>
          <p className="text-success font-mono text-sm">57.1%</p>
        </div>
        <div className="text-center p-2 bg-bg-tertiary rounded">
          <p className="text-text-muted text-xs">交付率</p>
          <p className="text-success font-mono text-sm">75.3%</p>
        </div>
      </div>
    </Panel>
  )
}

// Panel 4: 节点健康
function NodeHealthPanel() {
  const nodes = [
    { name: 'node-001 主节点', status: 'online', agents: '42/45', cpu: 32, mem: 40, latency: 12 },
    { name: 'node-002 备用节点', status: 'warning', agents: '35/38', cpu: 67, mem: 72, latency: 28 },
    { name: 'node-003 开发节点', status: 'online', agents: '10/12', cpu: 12, mem: 25, latency: 8 },
  ]

  return (
    <Panel title="节点健康状态">
      <div className="space-y-2">
        {nodes.map(node => (
          <div key={node.name}
            className={`p-3 rounded-lg border ${
              node.status === 'online' ? 'border-border-primary bg-bg-tertiary/50' :
              node.status === 'warning' ? 'border-warning/50 bg-warning/10' :
              'border-danger/50 bg-danger/10'
            }`}>
            <div className="flex justify-between items-center mb-2">
              <span className="text-text-primary text-sm font-medium">{node.name}</span>
              <span className={`text-xs ${
                node.status === 'online' ? 'text-success' :
                node.status === 'warning' ? 'text-warning' : 'text-danger'
              }`}>
                {node.status === 'online' ? '🟢' : node.status === 'warning' ? '🟡' : '🔴'}
              </span>
            </div>
            <div className="flex gap-4 text-xs text-text-muted">
              <span>Agent: {node.agents}</span>
              <span>CPU: {node.cpu}%</span>
              <span>MEM: {node.mem}%</span>
              <span>延迟: {node.latency}ms</span>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 p-2 bg-bg-tertiary rounded text-xs space-y-1">
        <p className="text-text-muted">服务状态</p>
        <div className="flex gap-4">
          <span className="text-success">✅ LLM</span>
          <span className="text-success">✅ Blockchain</span>
          <span className="text-warning">⚠️ Notification</span>
        </div>
      </div>
    </Panel>
  )
}

export default function CommandCenterPage() {
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [refreshInterval, setRefreshInterval] = useState(5000)
  const [isPaused, setIsPaused] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())

  // 时钟
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // 全屏
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  return (
    <div className="fixed inset-0 bg-bg-primary z-50 flex flex-col">
      {/* Header */}
      <div className="h-14 bg-bg-secondary border-b border-border-primary flex items-center px-6 gap-4 shrink-0">
        <Monitor className="w-5 h-5 text-primary" />
        <h1 className="font-orbitron text-lg text-text-primary">USMSB 指挥中心</h1>

        <div className="ml-auto flex items-center gap-4">
          {/* 时间 */}
          <div className="font-orbitron text-text-primary text-sm">
            {currentTime.toLocaleString('zh-CN', {
              year: 'numeric', month: '2-digit', day: '2-digit',
              hour: '2-digit', minute: '2-digit', second: '2-digit',
            })}
          </div>

          {/* 刷新间隔 */}
          <select
            value={refreshInterval}
            onChange={e => setRefreshInterval(Number(e.target.value))}
            className="bg-bg-tertiary text-text-primary text-sm rounded px-3 py-1.5 border border-border-primary outline-none"
          >
            <option value={5000}>5s 刷新</option>
            <option value={10000}>10s 刷新</option>
            <option value={30000}>30s 刷新</option>
            <option value={0}>暂停刷新</option>
          </select>

          {/* 控制按钮 */}
          <button onClick={() => setIsPaused(!isPaused)}
            className={`p-2 rounded-lg transition-colors ${isPaused ? 'bg-warning/20 text-warning' : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'}`}>
            {isPaused ? <RefreshCw className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>

          <button onClick={toggleFullscreen}
            className="p-2 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary transition-colors">
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          <button className="p-2 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary transition-colors">
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 4 分区面板 */}
      <div className="flex-1 grid grid-cols-2 gap-4 p-4 overflow-hidden">
        <AgentStatusPanel />
        <TransactionPanel />
        <MatchingPanel />
        <NodeHealthPanel />
      </div>

      {/* 底部控制栏 */}
      <div className="h-12 bg-bg-secondary border-t border-border-primary flex items-center px-6 gap-4 shrink-0">
        <div className="flex items-center gap-2 text-danger text-sm">
          <Bell className="w-4 h-4" />
          <span>暂无告警</span>
        </div>
        <div className="flex-1" />
        <span className="text-text-muted text-xs">
          {isPaused ? '⏸ 已暂停刷新' : `每 ${refreshInterval / 1000}s 刷新`}
        </span>
      </div>
    </div>
  )
}
