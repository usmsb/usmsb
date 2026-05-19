// NodeDetailDrawer.tsx - 节点详情抽屉
import { X, Server, Cpu, HardDrive, Wifi, Activity, ExternalLink } from 'lucide-react'
import StatusBadge from '../shared/StatusBadge'
import AddressDisplay from '../shared/AddressDisplay'

interface NodeDetailDrawerProps {
  node: {
    node_id: string
    name?: string
    status: string
    endpoint?: string
    region?: string
    cpu_percent?: number
    memory_percent?: number
    disk_percent?: number
    uptime?: number
    version?: string
    wallet_address?: string
    last_heartbeat?: number
    tx_count?: number
  } | null
  isOpen: boolean
  onClose: () => void
}

function NodeStatusIndicator({ status }: { status: string }) {
  const colors: Record<string, string> = {
    online: 'bg-success', offline: 'bg-danger', degraded: 'bg-warning',
  }
  const labels: Record<string, string> = {
    online: '在线', offline: '离线', degraded: '降级',
  }
  return (
    <div className="flex items-center gap-2">
      <div className={`w-2.5 h-2.5 rounded-full ${colors[status] || 'bg-text-muted'} ${status === 'online' ? 'animate-pulse' : ''}`} />
      <span className="text-text-primary">{labels[status] || status}</span>
    </div>
  )
}

export default function NodeDetailDrawer({ node, isOpen, onClose }: NodeDetailDrawerProps) {
  if (!isOpen || !node) return null

  const metrics = [
    { label: 'CPU', value: node.cpu_percent ?? 0, icon: Cpu },
    { label: '内存', value: node.memory_percent ?? 0, icon: HardDrive },
    { label: '磁盘', value: node.disk_percent ?? 0, icon: Activity },
  ]

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-bg-secondary border-l border-border-primary shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-info/10 flex items-center justify-center">
              <Server className="w-5 h-5 text-info" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text-primary font-rajdhani">
                {node.name || '节点详情'}
              </h2>
              <p className="text-xs text-text-muted font-mono">{node.node_id.slice(0, 12)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* 状态 */}
          <div className="flex items-center justify-between">
            <NodeStatusIndicator status={node.status} />
            {node.version && (
              <span className="text-xs bg-bg-tertiary text-text-muted px-2 py-1 rounded">
                v{node.version}
              </span>
            )}
          </div>

          {/* 性能指标 */}
          <div className="space-y-3">
            <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
              <Cpu className="w-4 h-4" /> 性能监控
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {metrics.map(m => (
                <div key={m.label} className="bg-bg-tertiary rounded-xl p-3 text-center">
                  <m.icon className="w-4 h-4 text-text-muted mx-auto mb-1" />
                  <p className="text-2xl font-bold font-mono text-text-primary">
                    {(m.value ?? 0).toFixed(0)}%
                  </p>
                  <p className="text-xs text-text-muted">{m.label}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 连接信息 */}
          <div className="space-y-3">
            <h3 className="text-text-primary font-rajdhani font-semibold flex items-center gap-2">
              <Wifi className="w-4 h-4" /> 连接信息
            </h3>
            <div className="space-y-2">
              {[
                ['区域', node.region || '-'],
                ['端点', node.endpoint || '-'],
                ['运行时间', node.uptime ? `${Math.floor(node.uptime / 3600)}h` : '-'],
                ['交易数', node.tx_count?.toLocaleString() ?? '-'],
                ['最后心跳', node.last_heartbeat ? new Date(node.last_heartbeat * 1000).toLocaleString('zh-CN') : '-'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between items-center py-2 border-b border-border-primary/30 last:border-0">
                  <span className="text-text-muted text-sm">{label}</span>
                  <span className="text-text-primary text-sm font-mono">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 钱包地址 */}
          {node.wallet_address && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold">钱包地址</h3>
              <AddressDisplay address={node.wallet_address} explorer="https://sepolia.basescan.org/address/" />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
