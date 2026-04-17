import { Search } from 'lucide-react'
import WalletAddress from '@/components/ui/WalletAddress'
import DataTable from '@/components/ui/DataTable'
import CyberInput from '@/components/ui/CyberInput'
import { formatVibe, timeAgo } from '@/lib/utils'
import type { WalletUser } from '@/types/user'

export default function UsersPage() {
  const mockUsers: WalletUser[] = [
    { wallet_address: '0x1234567890abcdef1234567890abcdef12345678', vibe_balance: 5000, total_consumption: 1234.56, total_requests: 567, created_at: new Date(Date.now() - 86400000 * 30).toISOString(), last_active: new Date(Date.now() - 3600000).toISOString() },
    { wallet_address: '0xabcdef1234567890abcdef1234567890abcdef12', vibe_balance: 3000, total_consumption: 890.12, total_requests: 234, created_at: new Date(Date.now() - 86400000 * 20).toISOString(), last_active: new Date(Date.now() - 7200000).toISOString() },
    { wallet_address: '0xfedcba0987654321fedcba0987654321fedcba09', vibe_balance: 10000, total_consumption: 3456.78, total_requests: 890, created_at: new Date(Date.now() - 86400000 * 10).toISOString(), last_active: new Date(Date.now() - 1800000).toISOString() },
  ]

  const columns = [
    { key: 'wallet', header: 'Wallet Address', render: (u: WalletUser) => <WalletAddress address={u.wallet_address} chars={6} /> },
    { key: 'balance', header: 'Balance', render: (u: WalletUser) => <span className="font-mono text-neon-blue">{formatVibe(u.vibe_balance)}</span> },
    { key: 'consumption', header: 'Total Consumption', render: (u: WalletUser) => <span className="font-mono text-text-secondary">{formatVibe(u.total_consumption)}</span> },
    { key: 'requests', header: 'Requests', render: (u: WalletUser) => <span className="font-mono text-xs">{u.total_requests.toLocaleString()}</span> },
    { key: 'last_active', header: 'Last Active', render: (u: WalletUser) => <span className="text-xs text-text-secondary">{timeAgo(u.last_active)}</span> },
    { key: 'created', header: 'Joined', render: (u: WalletUser) => <span className="text-xs text-text-secondary">{timeAgo(u.created_at)}</span> },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">WALLET USERS</h1>
      <div className="flex gap-4">
        <div className="flex-1 max-w-sm">
          <CyberInput placeholder="Search wallet address..."            prefixIcon={<Search size={14} className="text-text-secondary" />}/>
        </div>
      </div>
      <DataTable columns={columns} data={mockUsers} keyExtractor={u => u.wallet_address} emptyMessage="No users found" />
    </div>
  )
}
