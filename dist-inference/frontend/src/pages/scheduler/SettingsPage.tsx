import CyberInput from '@/components/ui/CyberInput'
import CyberButton from '@/components/ui/CyberButton'

export default function SettingsPage() {
  return (
    <div className="space-y-6 max-w-2xl">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">SETTINGS</h1>

      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">PLATFORM CONFIGURATION</h3>
        <CyberInput label="Platform Name" defaultValue="USMSB Distributed Inference" />
        <CyberInput label="Scheduler URL" defaultValue="http://192.168.1.1:8000" />
        <CyberInput label="API Rate Limit" defaultValue="100 req/min" />
      </div>

      <div className="cyber-card p-6 space-y-4">
        <h3 className="font-orbitron text-xs text-neon-blue tracking-widest">BILLING PARAMETERS</h3>
        <CyberInput label="GPU Time Rate (VIBE/sec/GPU)" defaultValue="0.001" type="number" />
        <CyberInput label="Token Rate (VIBE/1K tokens)" defaultValue="0.001" type="number" />
        <CyberInput label="Platform Share (%)" defaultValue="30" type="number" />
      </div>

      <div className="flex gap-3">
        <CyberButton variant="primary">Save Changes</CyberButton>
        <CyberButton variant="secondary">Reset</CyberButton>
      </div>
    </div>
  )
}
