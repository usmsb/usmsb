import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { X, ChevronRight, Lightbulb } from 'lucide-react'
import clsx from 'clsx'

interface FeatureTip {
  id: string
  targetSelector: string
  titleKey: string
  descKey: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  action?: {
    labelKey: string
    href?: string
    onClick?: () => void
  }
}

const STORAGE_KEY = 'usmsb_dismissed_tips'

export function FeatureSpotlight() {
  const { t } = useTranslation()
  const [activeTip, setActiveTip] = useState<FeatureTip | null>(null)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const [dismissedTips, setDismissedTips] = useState<string[]>([])

  // Load dismissed tips from localStorage
  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      try {
        setDismissedTips(JSON.parse(stored))
      } catch {
        // ignore parsing errors
      }
    }
  }, [])

  // Define feature tips - these can be triggered by different pages
  const featureTips: FeatureTip[] = [
    {
      id: 'publish-service',
      targetSelector: '[data-tip="publish-service"]',
      titleKey: 'tips.publishService.title',
      descKey: 'tips.publishService.desc',
      position: 'bottom',
      action: {
        labelKey: 'tips.publishService.action',
        href: '/app/publish/service',
      },
    },
    {
      id: 'matching-discover',
      targetSelector: '[data-tip="matching-discover"]',
      titleKey: 'tips.matchingDiscover.title',
      descKey: 'tips.matchingDiscover.desc',
      position: 'bottom',
    },
    {
      id: 'agent-register',
      targetSelector: '[data-tip="agent-register"]',
      titleKey: 'tips.agentRegister.title',
      descKey: 'tips.agentRegister.desc',
      position: 'bottom',
      action: {
        labelKey: 'tips.agentRegister.action',
        href: '/app/agents',
      },
    },
    {
      id: 'governance-vote',
      targetSelector: '[data-tip="governance-vote"]',
      titleKey: 'tips.governanceVote.title',
      descKey: 'tips.governanceVote.desc',
      position: 'bottom',
    },
  ]

  const showTip = useCallback((tipId: string) => {
    if (dismissedTips.includes(tipId)) return

    const tip = featureTips.find(t => t.id === tipId)
    if (!tip) return

    const target = document.querySelector(tip.targetSelector)
    if (!target) return

    const rect = target.getBoundingClientRect()
    const padding = 12

    let top = 0
    let left = 0

    switch (tip.position) {
      case 'top':
        top = rect.top - padding
        left = rect.left + rect.width / 2
        break
      case 'bottom':
        top = rect.bottom + padding
        left = rect.left + rect.width / 2
        break
      case 'left':
        top = rect.top + rect.height / 2
        left = rect.left - padding
        break
      case 'right':
        top = rect.top + rect.height / 2
        left = rect.right + padding
        break
      default:
        top = rect.bottom + padding
        left = rect.left + rect.width / 2
    }

    setPosition({ top, left: Math.max(150, Math.min(left, window.innerWidth - 300)) })
    setActiveTip(tip)
  }, [dismissedTips])

  const dismissTip = useCallback(() => {
    if (activeTip) {
      const newDismissed = [...dismissedTips, activeTip.id]
      setDismissedTips(newDismissed)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newDismissed))
      setActiveTip(null)
    }
  }, [activeTip, dismissedTips])

  // Listen for custom events to show tips
  useEffect(() => {
    const handleShowTip = (event: CustomEvent) => {
      showTip(event.detail.tipId)
    }

    window.addEventListener('showFeatureTip' as any, handleShowTip)
    return () => {
      window.removeEventListener('showFeatureTip' as any, handleShowTip)
    }
  }, [showTip])

  // Auto-show first undismissed tip on page load (optional)
  useEffect(() => {
    const timer = setTimeout(() => {
      const firstUndismissed = featureTips.find(tip => !dismissedTips.includes(tip.id))
      if (firstUndismissed) {
        const target = document.querySelector(firstUndismissed.targetSelector)
        if (target) {
          // Wait a bit for the page to settle
          setTimeout(() => showTip(firstUndismissed.id), 2000)
        }
      }
    }, 1000)

    return () => clearTimeout(timer)
  }, [dismissedTips, showTip])

  if (!activeTip) return null

  return (
    <>
      {/* Highlight overlay */}
      <div
        className="fixed inset-0 z-40 pointer-events-none"
        onClick={dismissTip}
      >
        {/* Dimmed background effect could be added here */}
      </div>

      {/* Tooltip */}
      <div
        className={clsx(
          'fixed z-50 w-72 p-4 rounded-xl shadow-xl',
          'bg-white dark:bg-secondary-800 border border-secondary-200 dark:border-secondary-700',
          'animate-scale-in'
        )}
        style={{
          top: position.top,
          left: position.left,
          transform: 'translateX(-50%)',
        }}
        role="tooltip"
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
              <Lightbulb className="w-4 h-4 text-primary-600 dark:text-primary-400" />
            </div>
            <h4 className="font-semibold text-secondary-900 dark:text-secondary-100">
              {t(activeTip.titleKey)}
            </h4>
          </div>
          <button
            onClick={dismissTip}
            className="p-1 rounded hover:bg-secondary-100 dark:hover:bg-secondary-700 text-secondary-400"
            aria-label="Dismiss"
          >
            <X size={14} />
          </button>
        </div>

        {/* Description */}
        <p className="text-sm text-secondary-600 dark:text-secondary-400 mb-3">
          {t(activeTip.descKey)}
        </p>

        {/* Action */}
        {activeTip.action && (
          <a
            href={activeTip.action.href}
            onClick={activeTip.action.onClick}
            className="flex items-center gap-1 text-sm font-medium text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300"
          >
            {t(activeTip.action.labelKey)}
            <ChevronRight size={14} />
          </a>
        )}
      </div>
    </>
  )
}

// Helper function to trigger a feature tip from anywhere
export function showFeatureTip(tipId: string) {
  const event = new CustomEvent('showFeatureTip', { detail: { tipId } })
  window.dispatchEvent(event)
}
