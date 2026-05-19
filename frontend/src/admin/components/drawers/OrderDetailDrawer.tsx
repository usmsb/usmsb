// OrderDetailDrawer.tsx - 订单详情抽屉
import { X, FileText, Clock, CheckCircle, AlertCircle, XCircle } from 'lucide-react'
import VIBEAmount from '../shared/VIBEAmount'
import AddressDisplay from '../shared/AddressDisplay'

interface OrderDetailDrawerProps {
  order: {
    order_id: string
    type?: string
    status: string
    amount: number
    agent_id?: string
    user_id?: string
    created_at?: number
    updated_at?: number
    description?: string
    tx_hash?: string
  } | null
  isOpen: boolean
  onClose: () => void
}

function OrderStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; icon: typeof CheckCircle; color: string; bg: string }> = {
    completed: { label: '已完成', icon: CheckCircle, color: 'text-success', bg: 'bg-success/10' },
    pending: { label: '待处理', icon: Clock, color: 'text-warning', bg: 'bg-warning/10' },
    failed: { label: '失败', icon: XCircle, color: 'text-danger', bg: 'bg-danger/10' },
    canceled: { label: '已取消', icon: XCircle, color: 'text-text-muted', bg: 'bg-text-muted/10' },
    active: { label: '进行中', icon: AlertCircle, color: 'text-info', bg: 'bg-info/10' },
  }
  const c = config[status] || { label: status, icon: Clock, color: 'text-text-muted', bg: 'bg-text-muted/10' }
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${c.color} ${c.bg}`}>
      <c.icon className="w-3 h-3" /> {c.label}
    </span>
  )
}

export default function OrderDetailDrawer({ order, isOpen, onClose }: OrderDetailDrawerProps) {
  if (!isOpen || !order) return null

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 z-50 w-full max-w-lg bg-bg-secondary border-l border-border-primary shadow-2xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-primary">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-text-primary font-rajdhani">订单详情</h2>
              <p className="text-xs text-text-muted font-mono">{order.order_id.slice(0, 12)}...</p>
            </div>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* 状态 + 金额 */}
          <div className="flex items-center justify-between">
            <OrderStatusBadge status={order.status} />
            <VIBEAmount value={order.amount} className="text-xl font-bold text-text-primary" />
          </div>

          {/* 基本信息 */}
          <div className="space-y-3">
            <h3 className="text-text-primary font-rajdhani font-semibold">基本信息</h3>
            <div className="space-y-2">
              {[
                ['订单类型', order.type || '-'],
                ['创建时间', order.created_at ? new Date(order.created_at * 1000).toLocaleString('zh-CN') : '-'],
                ['更新时间', order.updated_at ? new Date(order.updated_at * 1000).toLocaleString('zh-CN') : '-'],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between items-center py-2 border-b border-border-primary/30 last:border-0">
                  <span className="text-text-muted text-sm">{label}</span>
                  <span className="text-text-primary text-sm">{value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* 相关方 */}
          {(order.agent_id || order.user_id) && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold">相关方</h3>
              <div className="space-y-2">
                {order.agent_id && (
                  <div className="flex justify-between items-center py-2 border-b border-border-primary/30">
                    <span className="text-text-muted text-sm">Agent</span>
                    <AddressDisplay address={order.agent_id} textClassName="text-xs" />
                  </div>
                )}
                {order.user_id && (
                  <div className="flex justify-between items-center py-2 border-b border-border-primary/30">
                    <span className="text-text-muted text-sm">用户</span>
                    <AddressDisplay address={order.user_id} textClassName="text-xs" />
                  </div>
                )}
              </div>
            </div>
          )}

          {/* 描述 */}
          {order.description && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold">描述</h3>
              <p className="text-text-secondary text-sm bg-bg-tertiary rounded-lg p-3">{order.description}</p>
            </div>
          )}

          {/* 交易哈希 */}
          {order.tx_hash && (
            <div className="space-y-3">
              <h3 className="text-text-primary font-rajdhani font-semibold">交易哈希</h3>
              <AddressDisplay
                address={order.tx_hash}
                explorer="https://sepolia.basescan.org/tx/"
                textClassName="text-xs"
              />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
