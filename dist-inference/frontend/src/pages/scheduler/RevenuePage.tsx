import { DollarSign, TrendingUp, Users, Award } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import AreaTrendChart from '@/components/charts/AreaTrendChart'
import RevenuePieChart from '@/components/charts/RevenuePieChart'
import DataTable from '@/components/ui/DataTable'
import WalletAddress from '@/components/ui/WalletAddress'
import { formatVibe } from '@/lib/utils'

export default function RevenuePage() {
  // Mock data
  const trendData = Array.from({ length: 30 }, (_, i) => ({
    date: `Day ${i + 1}`,
    value: Math.floor(Math.random() * 5000) + 1000,
  }))

  const compositionData = [
    { name: 'GPU Time', value: 6500, color: '#00f5ff' },
    { name: 'Token Fee', value: 3500, color: '#bf00ff' },
  ]

  const nodeRankings = [
    { node_id: 'node_001', wallet: '0x1234567890abcdef', earnings: 2345.67, requests: 567 },
    { node_id: 'node_002', wallet: '0xabcdef1234567890', earnings: 1890.23, requests: 432 },
    { node_id: 'node_003', wallet: '0xfedcba0987654321', earnings: 1234.56, requests: 321 },
  ]

  const columns = [
    { key: 'rank', header: '#', render: (_: unknown, i: number) => <span className="font-mono text-neon-blue">{i + 1}</span> },
    { key: 'node_id', header: 'Node', render: (row: typeof nodeRankings[0]) => <span className="font-mono text-xs">{row.node_id}</span> },
    { key: 'wallet', header: 'Wallet', render: (row: typeof nodeRankings[0]) => <WalletAddress address={row.wallet} chars={6} /> },
    { key: 'requests', header: 'Requests', render: (row: typeof nodeRankings[0]) => <span className="font-mono text-xs">{row.requests}</span> },
    { key: 'earnings', header: 'Earnings', render: (row: typeof nodeRankings[0]) => <span className="font-mono text-neon-green">{formatVibe(row.earnings)} VIBE</span> },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">VIBE REVENUE CENTER</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Total Revenue" value={formatVibe(123456.78)} subValue="VIBE" icon={<DollarSign size={16} />} accent="blue" />
        <MetricCard label="Today" value={formatVibe(8234.56)} icon={<TrendingUp size={16} />} accent="green" trend={8} />
        <MetricCard label="This Month" value={formatVibe(34567.89)} icon={<TrendingUp size={16} />} accent="purple" trend={12} />
        <MetricCard label="Active Nodes" value={12} icon={<Users size={16} />} accent="blue" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">30-DAY REVENUE TREND</h3>
          <AreaTrendChart data={trendData} dataKey="value" color="#00f5ff" height={250} />
        </div>
        <div className="cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">COMPOSITION</h3>
          <RevenuePieChart data={compositionData} height={200} showLegend />
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm font-rajdhani">
              <span className="text-text-secondary">Platform Share (30%)</span>
              <span className="font-mono text-neon-red">-3,703.70 VIBE</span>
            </div>
            <div className="flex justify-between text-sm font-rajdhani">
              <span className="text-text-secondary">Node Payout (70%)</span>
              <span className="font-mono text-neon-green">+8,641.30 VIBE</span>
            </div>
          </div>
        </div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest flex items-center gap-2">
          <Award size={14} /> NODE RANKINGS
        </h3>
        <DataTable columns={columns} data={nodeRankings} keyExtractor={r => r.node_id} />
      </div>
    </div>
  )
}
