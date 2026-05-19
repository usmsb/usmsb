/**
 * StakeDistributionChart - Stake 等级分布图
 * 饼图 + 数值
 */
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from 'recharts'
import clsx from 'clsx'

interface StakeDistributionChartProps {
  data?: {
    none: number
    bronze: number
    silver: number
    gold: number
    platinum: number
  }
  loading?: boolean
  className?: string
}

const COLORS = ['#64748b', '#cd7c2d', '#a8a8a8', '#ffd700', '#6366f1']

export default function StakeDistributionChart({
  data,
  loading = false,
  className,
}: StakeDistributionChartProps) {
  if (loading) {
    return (
      <div className={clsx('flex items-center justify-center h-56 bg-bg-tertiary rounded-lg animate-pulse', className)}>
        <p className="text-text-muted text-sm">加载中...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className={clsx('flex items-center justify-center h-56 bg-bg-tertiary rounded-lg', className)}>
        <p className="text-text-muted text-sm">暂无数据</p>
      </div>
    )
  }

  const chartData = [
    { name: '无 Stake', value: data.none, color: COLORS[0] },
    { name: 'Bronze', value: data.bronze, color: COLORS[1] },
    { name: 'Silver', value: data.silver, color: COLORS[2] },
    { name: 'Gold', value: data.gold, color: COLORS[3] },
    { name: 'Platinum', value: data.platinum, color: COLORS[4] },
  ].filter(d => d.value > 0)

  const total = chartData.reduce((sum, d) => sum + d.value, 0)

  function CustomTooltip({ active, payload }: any) {
    if (!active || !payload?.length) return null
    const d = payload[0].payload
    return (
      <div className="bg-bg-elevated border border-border-primary rounded-lg p-3 shadow-lg">
        <p className="text-text-primary text-sm font-medium">{d.name}</p>
        <p className="text-text-secondary text-xs mt-1">
          {d.value.toLocaleString()} 人 ({((d.value / total) * 100).toFixed(1)}%)
        </p>
      </div>
    )
  }

  function CustomLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }: any) {
    if (percent < 0.05) return null
    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)
    return (
      <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central"
        fontSize={11} fontFamily="Rajdhani">
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  return (
    <div className={className}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            paddingAngle={2}
            dataKey="value"
            labelLine={false}
            label={<CustomLabel />}
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => <span className="text-text-secondary text-xs">{value}</span>}
            verticalAlign="bottom"
            height={36}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
