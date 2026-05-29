// TransactionChart.tsx - 交易趋势图 (recharts)
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const MOCK_TX_TREND = [
  { time: '00:00', transactions: 45, volume: 1200 },
  { time: '04:00', transactions: 30, volume: 800 },
  { time: '08:00', transactions: 80, volume: 2100 },
  { time: '12:00', transactions: 120, volume: 3400 },
  { time: '16:00', transactions: 95, volume: 2600 },
  { time: '20:00', transactions: 70, volume: 1900 },
  { time: '24:00', transactions: 50, volume: 1400 },
]

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number; name: string; color: string }>; label?: string }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-cyber-card border border-neon-purple/30 rounded-lg px-3 py-2 text-sm">
      <p className="text-gray-500 mb-1">{label}</p>
      {payload.map((p, i) => (
        <p key={i} className="font-mono" style={{ color: p.color }}>
          {p.name}: {Number(p.value).toLocaleString()}
        </p>
      ))}
    </div>
  )
}

interface TransactionChartProps {
  data?: Array<{ time: string; transactions: number; volume?: number }>
}

export default function TransactionChart({ data: propData }: TransactionChartProps) {
  const data = propData?.length ? propData : MOCK_TX_TREND

  return (
    <div>
      <ResponsiveContainer width="100%" height={160}>
        <BarChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(191, 0, 255, 0.1)" opacity={0.3} />
          <XAxis dataKey="time" tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fill: '#6b7280', fontSize: 11 }} tickLine={false} axisLine={false} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="transactions" name="交易数" fill="#bf00ff" radius={[3, 3, 0, 0]}
            style={{ filter: 'drop-shadow(0 0 5px rgba(191, 0, 255, 0.5))' }} />
        </BarChart>
      </ResponsiveContainer>
      <div className="flex justify-center gap-6 mt-2">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded-sm" style={{ background: '#bf00ff', boxShadow: '0 0 5px #bf00ff' }} />
          <span className="text-gray-500 text-xs">交易数</span>
        </div>
      </div>
    </div>
  )
}
