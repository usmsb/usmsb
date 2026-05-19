// Sparkline.tsx - 小型迷你趋势线图
import { LineChart, Line, ResponsiveContainer } from 'recharts'

interface SparklineProps {
  data: number[]
  color?: string
  width?: number
  height?: number
  className?: string
}

export default function Sparkline({
  data,
  color = '#8b5cf6',
  width = 80,
  height = 32,
  className = '',
}: SparklineProps) {
  const chartData = data.map((v, i) => ({ i, v }))

  if (!data || data.length < 2) {
    return <div className={`w-[${width}px] h-[${height}px] bg-bg-tertiary rounded ${className}`} />
  }

  return (
    <div className={className} style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line
            type="monotone"
            dataKey="v"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
