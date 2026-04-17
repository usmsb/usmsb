import { useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import Badge from '@/components/ui/Badge'
import WalletAddress from '@/components/ui/WalletAddress'
import DataTable from '@/components/ui/DataTable'
import ProgressBar from '@/components/ui/ProgressBar'
import CyberInput from '@/components/ui/CyberInput'
import CyberButton from '@/components/ui/CyberButton'
import { useGpuPool } from '@/hooks/useGpuPool'
import { formatNumber, formatVibe, timeAgo, truncateWallet } from '@/lib/utils'
import { useNavigate } from 'react-router-dom'
import type { GpuNode } from '@/types/gpu'

export default function NodesPage() {
  const navigate = useNavigate()
  const { data: nodes = [], isLoading, refetch } = useGpuPool()
  const [search, setSearch] = useState('')

  const filtered = nodes.filter(
    n => n.node_id.includes(search) || n.wallet_address.includes(search)
  )

  const columns = [
    {
      key: 'node_id',
      header: 'Node ID',
      render: (row: GpuNode) => (
        <span className="font-mono text-neon-blue text-sm">{row.node_id}</span>
      ),
    },
    {
      key: 'wallet',
      header: 'Wallet',
      render: (row: GpuNode) => <WalletAddress address={row.wallet_address} />,
    },
    {
      key: 'status',
      header: 'Status',
      render: (row: GpuNode) => <Badge status={row.status} dot />,
    },
    {
      key: 'gpu_count',
      header: 'GPU',
      render: (row: GpuNode) => <span className="font-mono">{row.gpu_count}x</span>,
    },
    {
      key: 'utilization',
      header: 'VRAM',
      render: (row: GpuNode) => {
        const used = row.gpus.reduce((s, g) => s + g.vram_used_gb, 0)
        const total = row.gpus.reduce((s, g) => s + g.vram_total_gb, 0)
        return <ProgressBar used={used} total={total} showLabel={false} height="sm" />
      },
    },
    {
      key: 'today_earnings',
      header: 'Today Earnings',
      render: (row: GpuNode) => (
        <span className="font-mono text-neon-green">{formatVibe(row.today_earnings)} VIBE</span>
      ),
    },
    {
      key: 'last_heartbeat',
      header: 'Last Heartbeat',
      render: (row: GpuNode) => (
        <span className="text-xs text-text-secondary">{timeAgo(row.last_heartbeat)}</span>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="font-orbitron text-xl font-bold neon-text-blue">GPU NODES</h1>
        <CyberButton variant="secondary" size="sm" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Refresh
        </CyberButton>
      </div>

      <div className="flex gap-4">
        <div className="flex-1 max-w-sm">
          <CyberInput
            placeholder="Search by Node ID or Wallet..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            prefixIcon={<Search size={14} className="text-text-secondary" />}
          />
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-text-secondary">Loading...</div>
      ) : (
        <DataTable
          columns={columns}
          data={filtered}
          keyExtractor={n => n.node_id}
          onRowClick={n => navigate(`/nodes/${n.node_id}`)}
          emptyMessage="No nodes found"
        />
      )}
    </div>
  )
}
