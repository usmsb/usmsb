import { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import WalletAddress from '@/components/ui/WalletAddress'
import DataTable from '@/components/ui/DataTable'
import CyberInput from '@/components/ui/CyberInput'
import { formatVibe, timeAgo } from '@/lib/utils'
import { fetchUsers } from '@/lib/api'
import { useNavigate } from 'react-router-dom'
import type { WalletUser } from '@/types/user'

export default function UsersPage() {
  const navigate = useNavigate()
  const [users, setUsers] = useState<WalletUser[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const loadUsers = (searchTerm?: string) => {
    setLoading(true)
    fetchUsers({ search: searchTerm, page_size: 100 })
      .then((data: Record<string, unknown>) => {
        const list = (data.users as WalletUser[]) || []
        setUsers(list)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const handleSearch = () => {
    setSearch(searchInput)
    loadUsers(searchInput)
  }

  const columns = [
    {
      key: 'wallet',
      header: 'Wallet Address',
      render: (u: WalletUser) => <WalletAddress address={u.wallet_address} chars={6} />,
    },
    {
      key: 'balance',
      header: 'Balance',
      render: (u: WalletUser) => <span className="font-mono text-neon-blue">{formatVibe(u.vibe_balance)}</span>,
    },
    {
      key: 'consumption',
      header: 'Total Consumption',
      render: (u: WalletUser) => <span className="font-mono text-text-secondary">{formatVibe(u.total_consumption)}</span>,
    },
    {
      key: 'requests',
      header: 'Requests',
      render: (u: WalletUser) => <span className="font-mono text-xs">{u.total_requests.toLocaleString()}</span>,
    },
    {
      key: 'last_active',
      header: 'Last Active',
      render: (u: WalletUser) => <span className="text-xs text-text-secondary">{timeAgo(u.last_active)}</span>,
    },
    {
      key: 'created',
      header: 'Joined',
      render: (u: WalletUser) => <span className="text-xs text-text-secondary">{timeAgo(u.created_at)}</span>,
    },
  ]

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">WALLET USERS</h1>
      <div className="flex gap-4">
        <div className="flex-1 max-w-sm">
          <CyberInput
            placeholder="Search wallet address..."
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSearch()}
            prefixIcon={<Search size={14} className="text-text-secondary" />}
          />
        </div>
      </div>
      {loading ? (
        <div className="text-center py-20 text-text-secondary">Loading...</div>
      ) : (
        <DataTable
          columns={columns}
          data={users}
          keyExtractor={u => u.wallet_address}
          onRowClick={u => navigate(`/users/${u.wallet_address}`)}
          emptyMessage="No users found"
        />
      )}
    </div>
  )
}
