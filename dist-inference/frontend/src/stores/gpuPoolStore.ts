import { create } from 'zustand'
import type { GpuNode } from '@/types/gpu'

interface GpuPoolState {
  nodes: GpuNode[]
  selectedNodeId: string | null
  setNodes: (nodes: GpuNode[]) => void
  updateNode: (nodeId: string, updates: Partial<GpuNode>) => void
  selectNode: (nodeId: string | null) => void
}

export const useGpuPoolStore = create<GpuPoolState>((set) => ({
  nodes: [],
  selectedNodeId: null,
  setNodes: (nodes) => set({ nodes }),
  updateNode: (nodeId, updates) =>
    set((state) => ({
      nodes: state.nodes.map((n) => (n.node_id === nodeId ? { ...n, ...updates } : n)),
    })),
  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),
}))
