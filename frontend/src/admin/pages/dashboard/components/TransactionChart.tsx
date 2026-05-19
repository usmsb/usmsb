/**
 * TransactionChart - 交易趋势组合图
 * Bar + Line 组合图
 */
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'
import clsx from 'clsx'

interface TransactionChartProps {
  className?: string
  // 简化版：生成模拟数据
  data?: { time: string; volume: number; count: number }[]
}

// 模拟数据（实际从 API 获取）
const mockData = Array.from({ length: 24 }, (_, i) => ({
  time: `${String(i).padStart(2, '0')}:00`,
  volume: Math.floor(Math.random() * 50000) + 10000,
  count: Math.floor(Math.random() * 100) + 20,
}))

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-elevated border border-border-primary rounded-lg p-3 shadow-lg">
      <p className="text-text-primary text-sm font-medium mb-2">{label}</p>
      <div className="space-y-1">
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full bg-primary" />
          <span className="text-text-secondary">交易额:</span>
          <span className="text-text-primary font-mono">
            {Number(payload[0]?.value || 0).toLocaleString()} VIBE
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <div className="w-2 h-2 rounded-full bg-success" />
          <span className="text-text-secondary">笔数:</span>
          <span className="text-text-primary font-mono">{payload[1]?.value?.toLocaleString() ?? '-'}</span>
        </div>
      </div>
    </div>
  )
}

export default function TransactionChart({ data = mockData, className }: TransactionChartProps) {
  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2d2d4a" vertical={false} />
          <XAxis
            dataKey="time"
            stroke="#64748b"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            interval={3}
          />
          <YAxis
            yAxisId="left"
            stroke="#64748b"
            fontSize={10}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#64748b"
            fontSize={10}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="text-text-secondary text-xs">
                {value === 'volume' ? '📊 交易额' : '📝 笔数'}
              </span>
            )}
          />

          <Bar
            yAxisId="left"
            dataKey="volume"
            name="volume"
            fill="#6366f1"
            opacity={0.8}
            radius={[2, 2, 0, 0]}
            maxBarSize={20}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="count"
            name="count"
            stroke="#10b981"
            strokeWidth={2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
