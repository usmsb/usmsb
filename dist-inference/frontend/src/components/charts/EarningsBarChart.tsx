import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'

interface Props {
  data: { name: string; value: number; color?: string }[]
  height?: number
}

const COLORS = ['#00f5ff', '#bf00ff', '#00ff88', '#ff00ff', '#ffd700']

export default function EarningsBarChart({ data, height = 200 }: Props) {
  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
          <XAxis
            dataKey="name"
            tick={{ fill: '#8888aa', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={{ stroke: '#1a1a2e' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#8888aa', fontSize: 10, fontFamily: 'JetBrains Mono' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={{
              background: '#0d0d14',
              border: '1px solid #1a1a2e',
              borderRadius: 6,
              color: '#e0e0ff',
              fontFamily: 'Rajdhani, sans-serif',
              fontSize: 13,
            }}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={data[index].color || COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}