import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface DataPoint {
  date?: string
  time?: string
  label?: string
  value: number
}

interface Props {
  data: DataPoint[]
  dataKey?: string
  color?: string
  height?: number
  label?: string
}

export default function AreaTrendChart({
  data,
  dataKey = 'value',
  color = '#00f5ff',
  height = 200,
}: Props) {
  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
          <defs>
            <linearGradient id={`gradient-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
          <XAxis
            dataKey="date"
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
            labelStyle={{ color: '#8888aa' }}
          />
          <Area
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            fill={`url(#gradient-${dataKey})`}
            dot={false}
            activeDot={{ r: 4, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}