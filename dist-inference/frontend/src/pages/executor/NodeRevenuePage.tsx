import { DollarSign, TrendingUp, Download } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import AreaTrendChart from '@/components/charts/AreaTrendChart'
import EarningsBarChart from '@/components/charts/EarningsBarChart'
import DataTable from '@/components/ui/DataTable'
import CyberButton from '@/components/ui/CyberButton'
import { formatVibe, formatDateTime } from '@/lib/utils'

export default function NodeRevenuePage() {
  const trendData = Array.from({ length: 30 }, (_, i) => ({
    date: `Day ${i + 1}`,
    value: Math.floor(Math.random() * 500) + 50,
  }))

  const compositionData = [
    { name: 'GPU Time', value: 650, color: '#00f5ff' },
    { name: 'Token Fee', value: 350, color: '#bf00ff' },
  ]

  const withdrawals = [
    { id: 'wd_001', amount_vibe: 1000, status: 'completed', created_at: new Date(Date.now() - 86400000).toISOString(), tx_hash: '0xabc123...' },
    { id: 'wd_002', amount_vibe: 500, status: 'pending', created_at: new Date().toISOString() },
  ]

  const columns = [
    { key: 'id', header: 'ID', render: (r: typeof withdrawals[0]) => <span className="font-mono text-xs text-neon-blue">{r.id}</span> },
    { key: 'amount', header: 'Amount', render: (r: typeof withdrawals[0]) => <span className="font-mono text-neon-green">{formatVibe(r.amount_vibe)}</span> },
    { key: 'status', header: 'Status', render: (r: typeof withdrawals[0]) => <span className="text-xs">{r.status}</span> },
    { key: 'time', header: 'Time', render: (r: typeof withdrawals[0]) => <span className="text-xs text-text-secondary">{formatDateTime(r.created_at)}</span> },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">VIBE REVENUE CENTER</h1>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Total Earnings" value={formatVibe(12345.67)} subValue="VIBE" icon={<DollarSign size={16} />} accent="blue" />
        <MetricCard label="This Month" value={formatVibe(3456.78)} subValue="VIBE" icon={<TrendingUp size={16} />} accent="purple" />
        <MetricCard label="Today" value={formatVibe(234.56)} subValue="VIBE" icon={<TrendingUp size={16} />} accent="green" trend={15} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">EARNINGS TREND (30 DAYS)</h3>
          <AreaTrendChart data={trendData} dataKey="value" color="#00f5ff" height={200} />
        </div>
        <div className="cyber-card p-4">
          <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">EARNINGS COMPOSITION</h3>
          <EarningsBarChart data={compositionData} height={200} />
          <div className="mt-4 p-3 bg-black/20 rounded-lg">
            <div className="flex justify-between text-sm font-rajdhani mb-1">
              <span className="text-text-secondary">Platform Share (30%)</span>
              <span className="font-mono text-neon-red">-3,456.00 VIBE</span>
            </div>
            <div className="flex justify-between text-sm font-rajdhani">
              <span className="text-text-secondary">Net Earning</span>
              <span className="font-mono text-neon-green">8,064.00 VIBE</span>
            </div>
          </div>
        </div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">WITHDRAWAL RECORDS</h3>
        <DataTable columns={columns} data={withdrawals} keyExtractor={r => r.id} emptyMessage="No withdrawals" />
        <div className="mt-4">
          <CyberButton variant="primary">
            <Download size={14} />
            Request Payout
          </CyberButton>
        </div>
      </div>
    </div>
  )
}
