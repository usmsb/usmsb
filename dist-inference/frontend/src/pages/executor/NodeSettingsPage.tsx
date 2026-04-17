import { useState } from 'react'
import CyberInput from '@/components/ui/CyberInput'
import CyberButton from '@/components/ui/CyberButton'
import WalletAddress from '@/components/ui/WalletAddress'
import { useAuthStore } from '@/stores/authStore'

export default function NodeSettingsPage() {
  const { walletAddress } = useAuthStore()
  const [maintenanceMode, setMaintenanceMode] = useState<'normal' | 'maintenance' | 'offline'>('normal')
  const [preloadModels, setPreloadModels] = useState({
    'Qwen/Qwen2.5-7B-Instruct': true,
    'Qwen/Qwen2.5-14B-Instruct': false,
  })

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">NODE SETTINGS</h1>

      {/* Wallet Settings */}
      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">WALLET SETTINGS</h3>
        <p className="text-xs text-text-secondary font-rajdhani">Wallet address receives all VIBE earnings</p>
        <div className="p-3 bg-black/20 rounded-lg border border-cyber-border">
          <WalletAddress address={walletAddress || '0x0000000000000000000000000000000000000000'} chars={8} />
        </div>
        <CyberInput label="New Wallet Address" placeholder="0x..." />
        <CyberInput label="Confirm Wallet Address" placeholder="0x..." />
        <CyberButton variant="primary" size="sm">Save Wallet</CyberButton>
      </div>

      {/* Preload Models */}
      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">PRELOAD MODEL SETTINGS</h3>
        <p className="text-xs text-text-secondary font-rajdhani">Auto-load on startup</p>
        {Object.entries(preloadModels).map(([model, enabled]) => (
          <label key={model} className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={enabled}
              onChange={e => setPreloadModels(prev => ({ ...prev, [model]: e.target.checked }))}
              className="w-4 h-4 accent-neon-blue"
            />
            <span className="font-rajdhani text-sm">{model}</span>
          </label>
        ))}
        <CyberInput label="GPU Utilization Threshold (%)" defaultValue="80" type="number" />
        <div className="flex gap-3">
          <CyberButton variant="primary" size="sm">Save</CyberButton>
          <CyberButton variant="secondary" size="sm">Reset to Default</CyberButton>
        </div>
      </div>

      {/* Maintenance Mode */}
      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">MAINTENANCE MODE</h3>
        {[
          { value: 'normal', label: 'Normal Mode', desc: 'Accept Inference Requests' },
          { value: 'maintenance', label: 'Maintenance Mode', desc: 'Reject New, Complete Current' },
          { value: 'offline', label: 'Offline Mode', desc: 'Shutdown' },
        ].map(opt => (
          <label key={opt.value} className="flex items-center gap-3 cursor-pointer p-2 rounded hover:bg-neon-blue/5">
            <input
              type="radio"
              name="maintenance"
              value={opt.value}
              checked={maintenanceMode === opt.value}
              onChange={e => setMaintenanceMode(e.target.value as typeof maintenanceMode)}
              className="accent-neon-blue"
            />
            <div>
              <div className="font-rajdhani text-sm text-text-primary">{opt.label}</div>
              <div className="text-xs text-text-secondary">{opt.desc}</div>
            </div>
          </label>
        ))}
        <CyberInput label="Maintenance Reason" placeholder="Enter reason..." />
        <CyberButton variant="danger" size="sm">Apply</CyberButton>
      </div>

      {/* About */}
      <div className="cyber-card p-6 space-y-2">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">ABOUT</h3>
        <div className="text-sm font-rajdhani text-text-secondary">USMSB Node Executor v0.1.0</div>
        <div className="text-sm font-rajdhani text-text-secondary">Build: 2026-04-17</div>
        <CyberButton variant="ghost" size="sm">Check for Updates</CyberButton>
      </div>
    </div>
  )
}
