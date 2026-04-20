import { useState, useEffect } from 'react'
import { DollarSign, TrendingUp, Download } from 'lucide-react'
import MetricCard from '@/components/ui/MetricCard'
import AreaTrendChart from '@/components/charts/AreaTrendChart'
import EarningsBarChart from '@/components/charts/EarningsBarChart'
import DataTable from '@/components/ui/DataTable'
import CyberButton from '@/components/ui/CyberButton'
import Modal from '@/components/ui/Modal'
import CyberInput from '@/components/ui/CyberInput'
import { formatVibe, formatDateTime } from '@/lib/utils'
import { fetchNodeEarnings, fetchWithdrawals, fetchNodeStatus, apiClient } from '@/lib/api'
import toast from 'react-hot-toast'

interface EarningsData {
  total_revenue_vibe: number
  total_requests: number
  trend: Array<{ date: string; revenue_vibe: number; requests: number }>
}

interface WithdrawalRecord {
  id: string
  amount_vibe: number
  status: string
  created_at: string
  tx_hash?: string
}

export default function NodeRevenuePage() {
  const [earnings, setEarnings] = useState<EarningsData | null>(null)
  const [withdrawals, setWithdrawals] = useState<WithdrawalRecord[]>([])
  const [showPayoutModal, setShowPayoutModal] = useState(false)
  const [payoutAmount, setPayoutAmount] = useState('')
  const [walletAddress, setWalletAddress] = useState('')
  const [requesting, setRequesting] = useState(false)

  useEffect(() => {
    fetchNodeEarnings({ days: 30 })
      .then((data: unknown) => setEarnings(data as EarningsData))
      .catch(() => {})

    fetchWithdrawals({ page_size: 20 })
      .then((data: unknown) => {
        const d = data as { withdrawals: WithdrawalRecord[] }
        setWithdrawals(d.withdrawals || [])
      })
      .catch(() => {})

    fetchNodeStatus()
      .then((data: unknown) => {
        const d = data as { wallet_address?: string }
        if (d.wallet_address) setWalletAddress(d.wallet_address)
      })
      .catch(() => {})
  }, [])

  const handleRequestPayout = async () => {
    if (!walletAddress) {
      toast.error('No wallet address configured')
      return
    }
    const amount = parseFloat(payoutAmount)
    if (!amount || amount <= 0) {
      toast.error('Invalid amount')
      return
    }
    setRequesting(true)
    try {
      await apiClient.post('/revenue/withdraw', { wallet_address: walletAddress, amount_vibe: amount })
      toast.success('Withdrawal requested')
      setShowPayoutModal(false)
      setPayoutAmount('')
      fetchWithdrawals({ page_size: 20 })
        .then((data: unknown) => {
          const d = data as { withdrawals: WithdrawalRecord[] }
          setWithdrawals(d.withdrawals || [])
        })
        .catch(() => {})
    } catch (e) {
      toast.error(String(e))
    } finally {
      setRequesting(false)
    }
  }

  const trendData = earnings?.trend?.map(d => ({
    date: d.date.slice(5),
    value: Math.round(d.revenue_vibe),
  })) || Array.from({ length: 30 }, (_, i) => ({
    date: `Day ${i + 1}`,
    value: Math.floor(Math.random() * 500) + 50,
  }))

  const compositionData = [
    { name: 'GPU Time', value: Math.round((earnings?.total_revenue_vibe || 0) * 0.7), color: '#00f5ff' },
    { name: 'Token Fee', value: Math.round((earnings?.total_revenue_vibe || 0) * 0.3), color: '#bf00ff' },
  ]

  const columns = [
    {
      key: 'id',
      header: 'ID',
      render: (r: WithdrawalRecord) => <span className="font-mono text-xs text-neon-blue">{r.id}</span>,
    },
    {
      key: 'amount',
      header: 'Amount',
      render: (r: WithdrawalRecord) => <span className="font-mono text-neon-green">{formatVibe(r.amount_vibe)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (r: WithdrawalRecord) => <span className="text-xs">{r.status}</span>,
    },
    {
      key: 'time',
      header: 'Time',
      render: (r: WithdrawalRecord) => <span className="text-xs text-text-secondary">{formatDateTime(r.created_at)}</span>,
    },
  ]

  const totalEarnings = earnings?.total_revenue_vibe || 12345.67
  const todayEarnings = earnings?.trend?.[earnings.trend.length - 1]?.revenue_vibe || 234.56
  const monthEarnings = earnings?.trend?.reduce((s, d) => s + d.revenue_vibe, 0) || 3456.78

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">VIBE REVENUE CENTER</h1>

      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Total Earnings" value={formatVibe(totalEarnings)} subValue="VIBE" icon={<DollarSign size={16} />} accent="blue" />
        <MetricCard label="This Month" value={formatVibe(monthEarnings)} subValue="VIBE" icon={<TrendingUp size={16} />} accent="purple" />
        <MetricCard label="Today" value={formatVibe(todayEarnings)} subValue="VIBE" icon={<TrendingUp size={16} />} accent="green" trend={15} />
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
              <span className="font-mono text-neon-red">-{formatVibe(totalEarnings * 0.3)} VIBE</span>
            </div>
            <div className="flex justify-between text-sm font-rajdhani">
              <span className="text-text-secondary">Net Earning</span>
              <span className="font-mono text-neon-green">{formatVibe(totalEarnings * 0.7)} VIBE</span>
            </div>
          </div>
        </div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">WITHDRAWAL RECORDS</h3>
        <DataTable columns={columns} data={withdrawals} keyExtractor={r => r.id} emptyMessage="No withdrawals" />
        <div className="mt-4">
          <CyberButton variant="primary" onClick={() => setShowPayoutModal(true)}>
            <Download size={14} />
            Request Payout
          </CyberButton>
        </div>
      </div>

      <Modal
        isOpen={showPayoutModal}
        onClose={() => setShowPayoutModal(false)}
        title="Request Payout"
        footer={
          <>
            <CyberButton variant="secondary" onClick={() => setShowPayoutModal(false)}>Cancel</CyberButton>
            <CyberButton variant="primary" onClick={handleRequestPayout} loading={requesting}>Confirm</CyberButton>
          </>
        }
      >
        <div className="space-y-4">
          <div>
            <div className="text-xs text-text-secondary mb-1">Wallet Address</div>
            <div className="font-mono text-sm text-neon-blue">{walletAddress || 'Not configured'}</div>
          </div>
          <CyberInput
            label="Amount (VIBE)"
            value={payoutAmount}
            onChange={e => setPayoutAmount(e.target.value)}
            placeholder="Enter amount..."
            type="number"
          />
          <div className="text-xs text-text-secondary">
            Available balance: {formatVibe(totalEarnings * 0.7)} VIBE
          </div>
        </div>
      </Modal>
    </div>
  )
}
