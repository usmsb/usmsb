/**
 * AgentTrendChart - Agent 活跃趋势图
 * 堆叠面积图（在线/忙碌/离线）
 */
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import clsx from 'clsx'

interface DataPoint {
  time: string
  online: number
  busy: number
  offline: number
  total?: number
}

interface AgentTrendChartProps {
  data: DataPoint[]
  timeRange: '7d' | '30d' | '90d'
  className?: string
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  const total = payload.reduce((sum: number, p: any) => sum + (p.value || 0), 0)
  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg p-3 shadow-lg">
      <p className="text-text-primary text-sm font-medium mb-2">{label}</p>
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-text-secondary">{p.name}:</span>
          <span className="text-text-primary font-mono">{p.value.toLocaleString()}</span>
        </div>
      ))}
      <div className="border-t border-border-primary mt-2 pt-2 flex justify-between text-xs">
        <span className="text-text-secondary">总计</span>
        <span className="text-text-primary font-mono font-medium">{total.toLocaleString()}</span>
      </div>
    </div>
  )
}

export default function AgentTrendChart({ data, timeRange, className }: AgentTrendChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={clsx('flex items-center justify-center h-64 bg-bg-tertiary rounded-lg', className)}>
        <p className="text-text-muted text-sm">暂无数据</p>
      </div>
    )
  }

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorOnline" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="colorBusy" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="colorOffline" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#2d2d4a" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            stroke="#64748b"
            fontSize={11}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="text-text-secondary text-xs">
                {value === 'online' ? '🟢 在线' :
                 value === 'busy' ? '🟡 忙碌' : '🔴 离线'}
              </span>
            )}
          />

          <Area
            type="monotone"
            dataKey="online"
            name="online"
            stackId="1"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#colorOnline)"
          />
          <Area
            type="monotone"
            dataKey="busy"
            name="busy"
            stackId="1"
            stroke="#f59e0b"
            strokeWidth={2}
            fill="url(#colorBusy)"
          />
          <Area
            type="monotone"
            dataKey="offline"
            name="offline"
            stackId="1"
            stroke="#ef4444"
            strokeWidth={2}
            fill="url(#colorOffline)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
