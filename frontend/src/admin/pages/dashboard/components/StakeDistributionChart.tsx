// StakeDistributionChart.tsx - 质押分布图 (recharts)
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useQuery } from '@tanstack/react-query'
import { fetchDashboard } from '../../../api/adminApi'

const MOCK_STAKE = [
  { name: 'Tier 1', value: 15000, color: '#6b7280' },
  { name: 'Tier 2', value: 28000, color: '#22c55e' },
  { name: 'Tier 3', value: 42000, color: '#3b82f6' },
  { name: 'Tier 4', value: 35000, color: '#f59e0b' },
  { name: 'Tier 5', value: 20000, color: '#ef4444' },
]

const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; value: number; color: string } }> }) => {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm">
      <p className="font-mono" style={{ color: d.color }}>{d.name}</p>
      <p className="text-text-primary font-mono">{d.value.toLocaleString()} VIBE</p>
    </div>
  )
}

export default function StakeDistributionChart() {
  const { data: dashboard } = useQuery({
    queryKey: ['admin', 'dashboard'],
    queryFn: fetchDashboard,
    refetchInterval: 60000,
  })

  const total = MOCK_STAKE.reduce((s, d) => s + d.value, 0)

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
      <h3 className="text-text-primary font-rajdhani font-semibold mb-3">质押分布</h3>
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie
            data={MOCK_STAKE}
            cx="50%"
            cy="50%"
            innerRadius={40}
            outerRadius={70}
            paddingAngle={3}
            dataKey="value"
          >
            {MOCK_STAKE.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="space-y-1.5">
        {MOCK_STAKE.map((entry, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: entry.color }} />
            <span className="text-text-muted text-xs flex-1">{entry.name}</span>
            <span className="text-text-secondary text-xs font-mono">{entry.value.toLocaleString()}</span>
            <span className="text-text-muted text-xs w-10 text-right">
              {((entry.value / total) * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
