import { useAuthStore } from '@/stores/authStore'
import { truncateWallet } from '@/lib/utils'
import { Wallet, Bell } from 'lucide-react'
import toast from 'react-hot-toast'

export default function TopBar() {
  const { walletAddress, isConnected } = useAuthStore()

  const copyAddress = () => {
    if (walletAddress) {
      navigator.clipboard.writeText(walletAddress)
      toast.success('Wallet address copied!')
    }
  }

  return (
    <header className="h-16 border-b border-cyber-border flex items-center justify-between px-6 bg-cyber-card/80 backdrop-blur-sm sticky top-0 z-40">
      <div className="flex items-center gap-3">
        <h2 className="font-orbitron text-sm text-text-secondary">
          Global Scheduler
        </h2>
      </div>
      <div className="flex items-center gap-4">
        {isConnected && walletAddress ? (
          <button
            onClick={copyAddress}
            className="flex items-center gap-2 text-xs font-mono text-neon-blue hover:text-neon-purple transition-colors"
          >
            <Wallet size={14} />
            {truncateWallet(walletAddress)}
          </button>
        ) : null}
        <button className="text-text-secondary hover:text-neon-blue transition-colors">
          <Bell size={18} />
        </button>
      </div>
    </header>
  )
}
