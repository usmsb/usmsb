import { useState } from 'react'
import { Wallet, Shield } from 'lucide-react'
import CyberButton from '@/components/ui/CyberButton'
import { useAuthStore } from '@/stores/authStore'
import { useNavigate } from 'react-router-dom'

export default function LoginPage() {
  const { setWallet, setConnecting, isConnecting } = useAuthStore()
  const navigate = useNavigate()
  const [mode, setMode] = useState<'connect' | 'anonymous'>('connect')

  const handleMockConnect = async () => {
    setConnecting(true)
    // Simulate wallet connection
    await new Promise(r => setTimeout(r, 1500))
    setWallet('0x' + Math.random().toString(16).slice(2, 42))
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-cyber-dark cyber-grid-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-12">
          <h1 className="font-orbitron text-3xl font-bold gradient-text tracking-widest mb-2">
            USMSB
          </h1>
          <p className="font-rajdhani text-text-secondary text-lg">
            Distributed Inference Network
          </p>
        </div>

        {/* Login Card */}
        <div className="cyber-card p-8">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-neon-blue/10 border border-neon-blue/30 mb-4">
              <Shield size={32} className="text-neon-blue" />
            </div>
            <h2 className="font-orbitron text-lg font-bold neon-text-blue">
              WALLET ACCESS
            </h2>
            <p className="text-text-secondary text-sm font-rajdhani mt-2">
              No email · No phone · Wallet only
            </p>
          </div>

          {mode === 'connect' ? (
            <div className="space-y-4">
              <CyberButton variant="primary" size="lg" className="w-full" onClick={handleMockConnect} loading={isConnecting}>
                <Wallet size={18} />
                Connect Wallet
              </CyberButton>

              <div className="relative flex items-center justify-center my-4">
                <div className="border-t border-cyber-border w-full" />
                <span className="absolute bg-cyber-card px-4 text-xs text-text-secondary">OR</span>
              </div>

              <CyberButton variant="secondary" size="lg" className="w-full" onClick={() => setMode('anonymous')}>
                Continue as Guest (Read-Only)
              </CyberButton>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-center text-sm text-text-secondary font-rajdhani">
                Anonymous mode allows viewing public data only.
              </p>
              <CyberButton variant="secondary" size="lg" className="w-full" onClick={() => { setMode('connect') }}>
                Back
              </CyberButton>
            </div>
          )}

          <div className="mt-6 text-center">
            <p className="text-xs text-text-secondary font-rajdhani">
              Powered by SIWE · Vibe Settlement · Web3 Native
            </p>
          </div>
        </div>

        <p className="text-center text-xs text-text-secondary mt-6 font-rajdhani">
          NO EMAIL · NO PHONE · WALLET ONLY
        </p>
      </div>
    </div>
  )
}
