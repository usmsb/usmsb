import { useState, useEffect } from 'react'
import CyberInput from '@/components/ui/CyberInput'
import CyberButton from '@/components/ui/CyberButton'
import { apiClient } from '@/lib/api'

const DEFAULT_SETTINGS = {
  platform_name: 'USMSB Distributed Inference',
  scheduler_url: 'http://localhost:8000',
  gpu_rate: 0.001,
  token_rate: 0.001,
  platform_share: 30,  // Display as percentage
}

export default function SettingsPage() {
  const [settings, setSettings] = useState(DEFAULT_SETTINGS)
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    apiClient.get('/settings')
      .then(r => {
        // Backend stores as decimal (0.30), frontend displays as percentage (30)
        const data = r.data
        setSettings({
          platform_name: data.platform_name || DEFAULT_SETTINGS.platform_name,
          scheduler_url: data.scheduler_url || DEFAULT_SETTINGS.scheduler_url,
          gpu_rate: data.gpu_rate ?? DEFAULT_SETTINGS.gpu_rate,
          token_rate: data.token_rate ?? DEFAULT_SETTINGS.token_rate,
          platform_share: (data.platform_share != null ? data.platform_share * 100 : DEFAULT_SETTINGS.platform_share),
        })
      })
      .catch(() => {})
  }, [])

  const handleSave = async () => {
    setLoading(true)
    setSaved(false)
    try {
      await apiClient.put('/settings', {
        platform_name: settings.platform_name,
        scheduler_url: settings.scheduler_url,
        gpu_rate: settings.gpu_rate,
        token_rate: settings.token_rate,
        platform_share: settings.platform_share / 100,  // Convert percentage to decimal
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch {
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setSettings(DEFAULT_SETTINGS)
  }

  const update = (key: string, value: string | number) => {
    setSettings(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">SETTINGS</h1>

      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">PLATFORM CONFIGURATION</h3>
        <CyberInput
          label="Platform Name"
          value={settings.platform_name}
          onChange={e => update('platform_name', e.target.value)}
        />
        <CyberInput
          label="Scheduler URL"
          value={settings.scheduler_url}
          onChange={e => update('scheduler_url', e.target.value)}
        />
        <CyberInput
          label="API Rate Limit"
          defaultValue="100 req/min"
          disabled
        />
      </div>

      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">BILLING PARAMETERS</h3>
        <CyberInput
          label="GPU Time Rate (VIBE/sec/GPU)"
          value={settings.gpu_rate}
          onChange={e => update('gpu_rate', parseFloat(e.target.value) || 0)}
          type="number"
        />
        <CyberInput
          label="Token Rate (VIBE/1K tokens)"
          value={settings.token_rate}
          onChange={e => update('token_rate', parseFloat(e.target.value) || 0)}
          type="number"
        />
        <CyberInput
          label="Platform Share (%)"
          value={settings.platform_share}
          onChange={e => update('platform_share', parseFloat(e.target.value) || 0)}
          type="number"
        />
      </div>

      <div className="flex gap-3">
        <CyberButton variant="primary" onClick={handleSave} loading={loading}>
          {saved ? 'Saved!' : 'Save Changes'}
        </CyberButton>
        <CyberButton variant="secondary" onClick={handleReset}>Reset</CyberButton>
      </div>
    </div>
  )
}
