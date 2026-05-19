// AgentTrendChart.tsx - Agent 趋势图 (recharts)
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const MOCK_TREND = [
  { time: '00:00', online: 12, busy: 5, offline: 3 },
  { time: '04:00', online: 10, busy: 4, offline: 6 },
  { time: '08:00', online: 18, busy: 8, offline: 4 },
  { time: '12:00', online: 22, busy: 12, offline: 2 },
  { time: '16:00', online: 20, busy: 10, offline: 4 },
  { time: '20:00', online: 16, busy: 7, offline: 5 },
  { time: '24:00', online: 14, busy: 6, offline: 6 },
]

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string; color: string }>; label?: string }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-mono" style={{ color: p.color }}>
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

interface AgentTrendChartProps {
  data?: Array<{ time: string; online: number; busy: number; offline?: number }>
}

export default function AgentTrendChart({ data: propData }: AgentTrendChartProps) {
  const data = propData?.length ? propData : MOCK_TREND

  return (
    <div className="bg-bg-secondary rounded-xl border border-border-primary p-4">
      <h3 className="text-text-primary font-rajdhani font-semibold mb-3">Agent 趋势 (24h)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="onlineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="busyGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
          <XAxis dataKey="time" tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Area type="monotone" dataKey="online" name="在线" stroke="#22c55e" fill="url(#onlineGrad)" strokeWidth={2} />
          <Area type="monotone" dataKey="busy" name="忙碌" stroke="#f59e0b" fill="url(#busyGrad)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-6 mt-2">
        {[
          { label: '在线', color: '#22c55e' },
          { label: '忙碌', color: '#f59e0b' },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 rounded" style={{ background: l.color }} />
            <span className="text-text-muted text-xs">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
