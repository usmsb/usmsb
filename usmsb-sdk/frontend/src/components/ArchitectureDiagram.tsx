/**
 * Architecture Diagram Renderer
 *
 * Detects ASCII art diagrams in markdown and renders them as visual diagrams
 * Supports: Box-drawing characters (┌─┐│└┘), Mermaid syntax
 *
 * TODO: 重写 asciiToMermaid 函数以正确处理分层架构图
 * - 问题：无法正确区分层内组件和层标题（│ 文本 │ 格式）
 * - 问题：嵌套的 │ 框线导致文本提取错误
 * - 建议：自定义解析器，分别提取层标题和层内组件
 */

import { useEffect, useRef, useState } from 'react'
import mermaid from 'mermaid'

// Initialize mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    useMaxWidth: true,
    htmlLabels: true,
    curve: 'basis',
  },
  themeVariables: {
    primaryColor: '#e0f2fe',
    primaryTextColor: '#0c4a6e',
    primaryBorderColor: '#0ea5e9',
    lineColor: '#64748b',
    secondaryColor: '#f1f5f9',
    tertiaryColor: '#f8fafc',
  },
})

interface DiagramProps {
  code: string
  type?: 'flowchart' | 'graph' | 'sequenceDiagram' | 'classDiagram' | 'stateDiagram' | 'erDiagram'
}

// Detect if text is ASCII architecture diagram
function isAsciiDiagram(text: string): boolean {
  // Box-drawing characters
  const boxChars = ['┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '─', '│', '╔', '╗', '╚', '╝', '═', '║']
  const boxCharsFound = boxChars.filter(char => text.includes(char))

  // Check for horizontal lines (single ─ or multiple)
  const hasHorizontalLines = text.includes('─') || text.includes('═') || text.includes('---')
  // Check for vertical lines
  const hasVerticalLines = text.includes('│') || text.includes('║')

  // Need at least 3 different box characters AND has lines
  return boxCharsFound.length >= 3 && (hasHorizontalLines || hasVerticalLines)
}

// Convert ASCII diagram to Mermaid flowchart
function asciiToMermaid(code: string): string {
  const lines = code.split('\n')

  // Check if it looks like a layered architecture
  const hasLayers = lines.some(line =>
    line.includes('─') || line.includes('═') || line.includes('┌') || line.includes('╔') || line.includes('┬') || line.includes('├')
  )

  if (!hasLayers) {
    return 'graph TD\nA[Diagram]'
  }

  let mermaidCode = 'graph TB\n'

  // Analyze the ASCII diagram structure:
  // - Layer titles are in single pipe │ text │
  // - Components in same layer are separated by spaces: ┌───┐ ┌───┐
  // - Layers are separated by ├ or ─ lines
  // - The entire diagram is wrapped in ┌─────┐ ... └─────┘

  interface Layer {
    title: string
    components: string[]
  }

  const layers: Layer[] = []

  // Find separator lines (├ or ─) which separate layers
  // These lines indicate the boundary between layers
  const separatorIndices: number[] = []

  lines.forEach((line, index) => {
    // Check if this is a separator line (├ or ─ or ═)
    // The pattern is: ├────┤ or ────── or ═════
    const trimmed = line.trim()
    // Separator line: contains ├ or ┤ or ┬ or ┴ or ─ or ═
    if (/[├┤┬┴─═]/.test(trimmed) && !/[┌┐└┘╔╗╚╝]/.test(trimmed)) {
      separatorIndices.push(index)
    }
  })

  // Now find layer titles
  // Layer titles are between separators
  // A layer title is │ text │ where text is not just border chars

  // Find all lines that contain │ text │ (single pipe, not ││)
  const potentialTitles: { lineIndex: number; title: string }[] = []

  lines.forEach((line, index) => {
    // Look for │ text │ pattern
    // Must start and end with │, and not be ││ (double pipe)
    const trimmed = line.trim()
    if (trimmed.startsWith('│') && trimmed.endsWith('│') && !trimmed.startsWith('││')) {
      // Extract the text between │
      const match = line.match(/│([^│]+)│/)
      if (match) {
        const text = match[1].trim()
        // Skip if it's just border characters
        if (text && !/^[─=]+$/.test(text)) {
          potentialTitles.push({ lineIndex: index, title: text })
        }
      }
    }
  })

  // Now, we need to filter out the outer diagram title (first one)
  // and keep only layer titles
  // The first │ title │ is usually the outer diagram title
  // Subsequent │ title │ are layer titles

  // Filter to get actual layer titles:
  // - Skip the first one if it's before the first separator
  // - Only keep titles that are followed by components

  const layerTitles: { lineIndex: number; title: string }[] = []

  // Find the first separator - anything before it is the diagram header
  const firstSeparatorIdx = separatorIndices.length > 0 ? separatorIndices[0] : -1

  potentialTitles.forEach((item, idx) => {
    // Skip the first title if it's before first separator (it's the diagram header)
    if (idx === 0 && firstSeparatorIdx >= 0 && item.lineIndex < firstSeparatorIdx) {
      return
    }
    layerTitles.push(item)
  })

  // Now extract components for each layer
  for (let i = 0; i < layerTitles.length; i++) {
    const currentTitle = layerTitles[i]
    const nextTitleLineIndex = layerTitles[i + 1]?.lineIndex ?? lines.length

    const layer: Layer = {
      title: currentTitle.title,
      components: []
    }

    // Look at lines between this title and next title (or end)
    for (let j = currentTitle.lineIndex + 1; j < nextTitleLineIndex; j++) {
      const line = lines[j]

      // Skip separator lines (├, ─, ═, etc)
      if (/^[\s]*[├┤┬┴─═║]+\s*$/.test(line)) {
        continue
      }

      // Skip lines that are just borders
      if (/^[│┌┐└┘╔╗╚╝─=║\s]+$/.test(line)) {
        continue
      }

      // Extract components from this line
      // Components are ┌───┐ blocks
      const boxPattern = /┌([^┐]+)┐/g
      let match
      while ((match = boxPattern.exec(line)) !== null) {
        const component = match[1].trim()
        if (component && component.length > 0) {
          layer.components.push(component)
        }
      }

      // Also try ╔╗ boxes
      const altBoxPattern = /╔([^╗]+)╗/g
      while ((match = altBoxPattern.exec(line)) !== null) {
        const component = match[1].trim()
        if (component && component.length > 0) {
          layer.components.push(component)
        }
      }
    }

    if (layer.components.length > 0 || layer.title) {
      layers.push(layer)
    }
  }

  // Build Mermaid code with subgraphs
  layers.forEach((layer, layerIdx) => {
    const safeTitle = layer.title.replace(/"/g, "'")
    mermaidCode += `  subgraph layer${layerIdx} ["${safeTitle}"]\n`

    // Add components as nodes
    layer.components.forEach((comp, compIdx) => {
      const shortText = comp.length > 20 ? comp.substring(0, 17) + '...' : comp
      const safeText = shortText.replace(/"/g, "'")
      mermaidCode += `    n${layerIdx}_${compIdx}["${safeText}"]\n`
    })

    // Connect components within the same layer
    for (let i = 0; i < layer.components.length - 1; i++) {
      mermaidCode += `    n${layerIdx}_${i} --> n${layerIdx}_${i + 1}\n`
    }

    mermaidCode += `  end\n`

    // Connect to next layer (last component to first component of next layer)
    if (layerIdx < layers.length - 1 && layer.components.length > 0) {
      const nextLayer = layers[layerIdx + 1]
      if (nextLayer.components.length > 0) {
        mermaidCode += `  n${layerIdx}_${layer.components.length - 1} --> n${layerIdx + 1}_0\n`
      }
    }
  })

  return mermaidCode || 'graph TD\nA[Diagram]'
}

export function ArchitectureDiagram({ code, type = 'flowchart' }: DiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [svg, setSvg] = useState<string>('')
  const [error, setError] = useState<string>('')

  useEffect(() => {
    async function renderDiagram() {
      try {
        // Check if it's a Mermaid diagram
        const isMermaidCode = code.trim().startsWith('graph') || code.trim().startsWith('flowchart') ||
            code.trim().startsWith('sequenceDiagram') || code.trim().startsWith('classDiagram')

        let mermaidCode = code
        if (!isMermaidCode) {
          // Try to convert ASCII to Mermaid
          mermaidCode = asciiToMermaid(code)
        }

        const { svg } = await mermaid.render(`mermaid-${Date.now()}`, mermaidCode)
        setSvg(svg)
      } catch (err) {
        console.error('Diagram render error:', err)
        setError(String(err))
        setSvg('')
      }
    }

    renderDiagram()
  }, [code, type])

  // If error, show error message
  if (error) {
    return <div className="text-red-500">Diagram error: {error}</div>
  }

  // If no diagram detected or error, return null
  if (!svg) {
    return null
  }

  return (
    <div
      ref={containerRef}
      className="my-6 p-4 bg-white dark:bg-secondary-800 rounded-lg border border-secondary-200 dark:border-secondary-700 overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  )
}

// ASCII Art Diagram Component - Enhanced display
interface AsciiDiagramProps {
  code: string
}

export function AsciiDiagram({ code }: AsciiDiagramProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (!isAsciiDiagram(code)) {
    return null
  }

  return (
    <div className="my-6 rounded-lg border border-secondary-200 dark:border-secondary-700 overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-2 bg-secondary-50 dark:bg-secondary-800 text-secondary-700 dark:text-secondary-300 hover:bg-secondary-100 dark:hover:bg-secondary-700 transition-colors"
      >
        <span className="flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16m-7 6h7" />
          </svg>
          <span className="text-sm font-medium">Architecture Diagram</span>
        </span>
        <svg
          className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Diagram Content */}
      {isExpanded && (
        <div className="p-4 overflow-x-auto bg-secondary-100 dark:bg-secondary-900">
          <pre className="text-xs md:text-sm font-mono text-secondary-800 dark:text-secondary-200 whitespace-pre">
{code}
          </pre>
        </div>
      )}
    </div>
  )
}

export default ArchitectureDiagram
