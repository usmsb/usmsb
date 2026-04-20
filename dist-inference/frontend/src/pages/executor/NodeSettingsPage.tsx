import { useState, useEffect } from 'react'
import CyberInput from '@/components/ui/CyberInput'
import CyberButton from '@/components/ui/CyberButton'
import WalletAddress from '@/components/ui/WalletAddress'
import { useAuthStore } from '@/stores/authStore'
import { updateNodeSettings, fetchNodeStatus } from '@/lib/api'
import toast from 'react-hot-toast'

export default function NodeSettingsPage() {
  const { walletAddress } = useAuthStore()
  const [maintenanceMode, setMaintenanceMode] = useState<'normal' | 'maintenance' | 'offline'>('normal')
  const [maintenanceReason, setMaintenanceReason] = useState('')
  const [gpuThreshold, setGpuThreshold] = useState(80)
  const [newWallet, setNewWallet] = useState('')
  const [confirmWallet, setConfirmWallet] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetchNodeStatus()
      .then((status: Record<string, unknown>) => {
        if (status.gpu_threshold) setGpuThreshold(status.gpu_threshold as number)
        if (status.maintenance_mode) setMaintenanceMode(status.maintenance_mode as 'normal' | 'maintenance' | 'offline')
        if (status.maintenance_reason) setMaintenanceReason(status.maintenance_reason as string)
        if (status.wallet_address) setNewWallet(status.wallet_address as string)
      })
      .catch(() => {})
  }, [])

  const handleSaveWallet = async () => {
    if (!newWallet) return
    if (newWallet !== confirmWallet) {
      toast.error('Wallet addresses do not match')
      return
    }
    setSaving(true)
    try {
      await updateNodeSettings({ wallet_address: newWallet })
      toast.success('Wallet updated')
      setConfirmWallet('')
    } catch (e) {
      toast.error(String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleSavePreload = async () => {
    setSaving(true)
    try {
      await updateNodeSettings({ gpu_threshold: gpuThreshold })
      toast.success('Settings saved')
    } catch (e) {
      toast.error(String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleResetDefault = async () => {
    setSaving(true)
    try {
      await updateNodeSettings({
        gpu_threshold: 80,
        maintenance_mode: 'normal',
        maintenance_reason: '',
      })
      setGpuThreshold(80)
      setMaintenanceMode('normal')
      setMaintenanceReason('')
      toast.success('Reset to defaults')
    } catch (e) {
      toast.error(String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleApplyMaintenance = async () => {
    setSaving(true)
    try {
      await updateNodeSettings({
        maintenance_mode: maintenanceMode,
        maintenance_reason: maintenanceReason,
      })
      toast.success('Maintenance mode updated')
    } catch (e) {
      toast.error(String(e))
    } finally {
      setSaving(false)
    }
  }

  const handleCheckUpdates = () => {
    toast.success('You are running the latest version')
  }

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
        <CyberInput
          label="New Wallet Address"
          value={newWallet}
          onChange={e => setNewWallet(e.target.value)}
          placeholder="0x..."
        />
        <CyberInput
          label="Confirm Wallet Address"
          value={confirmWallet}
          onChange={e => setConfirmWallet(e.target.value)}
          placeholder="0x..."
        />
        <CyberButton variant="primary" size="sm" onClick={handleSaveWallet} loading={saving}>
          Save Wallet
        </CyberButton>
      </div>

      {/* Preload Models */}
      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">PRELOAD MODEL SETTINGS</h3>
        <p className="text-xs text-text-secondary font-rajdhani">Auto-load on startup</p>
        <CyberInput
          label="GPU Utilization Threshold (%)"
          value={gpuThreshold}
          onChange={e => setGpuThreshold(parseInt(e.target.value) || 80)}
          type="number"
        />
        <div className="flex gap-3">
          <CyberButton variant="primary" size="sm" onClick={handleSavePreload} loading={saving}>
            Save
          </CyberButton>
          <CyberButton variant="secondary" size="sm" onClick={handleResetDefault}>
            Reset to Default
          </CyberButton>
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
        <CyberInput
          label="Maintenance Reason"
          value={maintenanceReason}
          onChange={e => setMaintenanceReason(e.target.value)}
          placeholder="Enter reason..."
        />
        <CyberButton variant="danger" size="sm" onClick={handleApplyMaintenance} loading={saving}>
          Apply
        </CyberButton>
      </div>

      {/* About */}
      <div className="cyber-card p-6 space-y-2">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">ABOUT</h3>
        <div className="text-sm font-rajdhani text-text-secondary">USMSB Node Executor v0.1.0</div>
        <div className="text-sm font-rajdhani text-text-secondary">Build: 2026-04-19</div>
        <CyberButton variant="ghost" size="sm" onClick={handleCheckUpdates}>
          Check for Updates
        </CyberButton>
      </div>
    </div>
  )
}
