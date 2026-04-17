import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'

interface Props {
  data: { name: string; value: number; color?: string }[]
  height?: number
  showLegend?: boolean
}

const COLORS = ['#00f5ff', '#bf00ff', '#00ff88', '#ff00ff', '#ffd700']

export default function RevenuePieChart({ data, height = 200, showLegend = false }: Props) {
  return (
    <div className="w-full">
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={80}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={data[index].color || COLORS[index % COLORS.length]}
                stroke="transparent"
              />
            ))}
          </Pie>
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
          {showLegend && (
            <Legend
              formatter={(value) => (
                <span className="text-xs font-rajdhani text-text-secondary">{value}</span>
              )}
            />
          )}
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}