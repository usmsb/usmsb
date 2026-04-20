import { useState, useEffect } from 'react'
import { Download, Upload } from 'lucide-react'
import ProgressBar from '@/components/ui/ProgressBar'
import CyberButton from '@/components/ui/CyberButton'
import Badge from '@/components/ui/Badge'
import { fetchNodeModels, fetchNodeStatus, loadModel, unloadModel } from '@/lib/api'
import toast from 'react-hot-toast'

interface ModelItem {
  model_id: string
  name: string
  is_loaded: boolean
  vram_required_gb: number
  total_requests: number
  total_tokens: number
}

interface NodeStatusData {
  gpu_info: {
    gpus: Array<{
      id: number
      vram_gb: number
      used_vram_gb: number
    }>
  }
}

export default function NodeModelsPage() {
  const [models, setModels] = useState<ModelItem[]>([])
  const [loadedModels, setLoadedModels] = useState<string[]>([])
  const [totalVram, setTotalVram] = useState(200)
  const [usedVram, setUsedVram] = useState(60)
  const [loadingId, setLoadingId] = useState<string | null>(null)

  useEffect(() => {
    fetchNodeModels()
      .then((data: unknown) => {
        const d = data as { models: ModelItem[] }
        const modelList = d.models || []
        setModels(modelList)
        setLoadedModels(modelList.filter((m: ModelItem) => m.is_loaded).map((m: ModelItem) => m.model_id))
      })
      .catch(() => {})

    fetchNodeStatus()
      .then((data: unknown) => {
        const status = data as NodeStatusData
        const gpus = status.gpu_info?.gpus || []
        const total = gpus.reduce((s: number, g: { vram_gb: number }) => s + g.vram_gb, 0)
        const used = gpus.reduce((s: number, g: { used_vram_gb: number }) => s + g.used_vram_gb, 0)
        setTotalVram(total || 200)
        setUsedVram(used || 60)
      })
      .catch(() => {})
  }, [])

  const availableVram = totalVram - usedVram

  const handleLoad = async (modelId: string) => {
    setLoadingId(modelId)
    try {
      await loadModel(modelId)
      toast.success(`${modelId} loaded`)
      setLoadedModels(prev => [...prev, modelId])
      fetchNodeModels()
        .then((data: unknown) => {
          const d = data as { models: ModelItem[] }
          setModels(d.models || [])
        })
        .catch(() => {})
    } catch (e) {
      toast.error(String(e))
    } finally {
      setLoadingId(null)
    }
  }

  const handleUnload = async (modelId: string) => {
    setLoadingId(modelId)
    try {
      await unloadModel(modelId)
      toast.success(`${modelId} unload requested`)
      setLoadedModels(prev => prev.filter(id => id !== modelId))
    } catch (e) {
      toast.error(String(e))
    } finally {
      setLoadingId(null)
    }
  }

  const loadedList = models.filter(m => m.is_loaded)
  const availableList = models.filter(m => !m.is_loaded)

  return (
    <div className="space-y-6">
      <h1 className="font-orbitron text-xl font-bold neon-text-blue">MODEL MANAGEMENT</h1>

      <div className="cyber-card p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-rajdhani text-text-secondary uppercase tracking-widest">GPU VRAM</span>
          <span className="font-mono text-xs text-neon-blue">{usedVram}GB / {totalVram}GB ({Math.round((usedVram/totalVram)*100)}%)</span>
        </div>
        <ProgressBar used={usedVram} total={totalVram} showLabel={false} height="md" />
        <div className="mt-2 text-xs text-text-secondary font-mono">Available: {availableVram}GB</div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">LOADED MODELS</h3>
        <div className="space-y-3">
          {loadedList.map(m => (
            <div key={m.model_id} className="flex items-center justify-between p-3 bg-black/20 rounded-lg border border-cyber-border">
              <div>
                <div className="font-rajdhani text-sm text-text-primary">{m.name}</div>
                <div className="text-xs text-text-secondary font-mono">VRAM: {m.vram_required_gb}GB · Requests: {m.total_requests}</div>
              </div>
              <div className="flex items-center gap-2">
                <Badge status="idle" label="LOADED" />
                <CyberButton
                  variant="ghost"
                  size="sm"
                  loading={loadingId === m.model_id}
                  onClick={() => handleUnload(m.model_id)}
                >
                  <Upload size={12} />
                  Unload
                </CyberButton>
              </div>
            </div>
          ))}
          {loadedList.length === 0 && (
            <div className="text-center py-8 text-text-secondary text-sm">No models loaded</div>
          )}
        </div>
      </div>

      <div className="cyber-card p-4">
        <h3 className="font-orbitron text-xs text-neon-blue mb-4 tracking-widest">AVAILABLE MODELS</h3>
        <div className="space-y-3">
          {availableList.map(m => {
            const canLoad = availableVram >= m.vram_required_gb
            return (
              <div key={m.model_id} className="flex items-center justify-between p-3 bg-black/20 rounded-lg border border-cyber-border">
                <div>
                  <div className="font-rajdhani text-sm text-text-primary">{m.name}</div>
                  <div className="text-xs text-text-secondary font-mono">Requires: {m.vram_required_gb}GB</div>
                </div>
                {canLoad ? (
                  <CyberButton
                    variant="primary"
                    size="sm"
                    loading={loadingId === m.model_id}
                    onClick={() => handleLoad(m.model_id)}
                  >
                    <Download size={12} />
                    Load
                  </CyberButton>
                ) : (
                  <span className="text-xs text-neon-yellow">⚠ Insufficient VRAM</span>
                )}
              </div>
            )
          })}
          {availableList.length === 0 && (
            <div className="text-center py-8 text-text-secondary text-sm">No available models</div>
          )}
        </div>
      </div>
    </div>
  )
}
