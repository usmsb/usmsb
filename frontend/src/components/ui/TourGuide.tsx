import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { X, ChevronLeft, ChevronRight, SkipForward, Sparkles } from 'lucide-react'
import clsx from 'clsx'

export interface TourStep {
  id: string
  target: string // CSS selector for target element
  title: string
  content: string
  position?: 'top' | 'bottom' | 'left' | 'right'
  spotlight?: boolean
}

interface TourGuideProps {
  steps: TourStep[]
  isActive: boolean
  onComplete: () => void
  onSkip: () => void
  startStep?: number
}

const TOUR_STORAGE_KEY = 'usmsb-tour-completed'

export function useTour(tourId: string) {
  const [isActive, setIsActive] = useState(false)

  useEffect(() => {
    const completedTours = JSON.parse(localStorage.getItem(TOUR_STORAGE_KEY) || '[]')
    if (!completedTours.includes(tourId)) {
      // Delay showing tour to allow page to render
      const timer = setTimeout(() => setIsActive(true), 1000)
      return () => clearTimeout(timer)
    }
  }, [tourId])

  const startTour = useCallback(() => {
    setIsActive(true)
  }, [])

  const completeTour = useCallback(() => {
    const completedTours = JSON.parse(localStorage.getItem(TOUR_STORAGE_KEY) || '[]')
    if (!completedTours.includes(tourId)) {
      completedTours.push(tourId)
      localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(completedTours))
    }
    setIsActive(false)
  }, [tourId])

  const resetTour = useCallback(() => {
    const completedTours = JSON.parse(localStorage.getItem(TOUR_STORAGE_KEY) || '[]')
    const filtered = completedTours.filter((id: string) => id !== tourId)
    localStorage.setItem(TOUR_STORAGE_KEY, JSON.stringify(filtered))
    setIsActive(true)
  }, [tourId])

  return { isActive, startTour, completeTour, resetTour }
}

export function TourGuide({ steps, isActive, onComplete, onSkip, startStep = 0 }: TourGuideProps) {
  const { t } = useTranslation()
  const [currentStep, setCurrentStep] = useState(startStep)
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })

  const step = steps[currentStep]

  useEffect(() => {
    if (!isActive || !step) return

    const updatePosition = () => {
      const target = document.querySelector(step.target)
      if (target) {
        const rect = target.getBoundingClientRect()
        setTargetRect(rect)

        // Calculate tooltip position
        const position = step.position || 'bottom'
        const tooltipWidth = 320
        const tooltipHeight = 200
        const padding = 16

        let x = 0
        let y = 0

        switch (position) {
          case 'top':
            x = rect.left + rect.width / 2 - tooltipWidth / 2
            y = rect.top - tooltipHeight - padding
            break
          case 'bottom':
            x = rect.left + rect.width / 2 - tooltipWidth / 2
            y = rect.bottom + padding
            break
          case 'left':
            x = rect.left - tooltipWidth - padding
            y = rect.top + rect.height / 2 - tooltipHeight / 2
            break
          case 'right':
            x = rect.right + padding
            y = rect.top + rect.height / 2 - tooltipHeight / 2
            break
        }

        // Keep tooltip in viewport
        x = Math.max(16, Math.min(x, window.innerWidth - tooltipWidth - 16))
        y = Math.max(16, Math.min(y, window.innerHeight - tooltipHeight - 16))

        setTooltipPosition({ x, y })

        // Scroll target into view
        target.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }

    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition)
    }
  }, [isActive, currentStep, step])

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      onComplete()
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    onSkip()
  }

  if (!isActive || !step || !targetRect) return null

  return (
    <div className="fixed inset-0 z-[9999]">
      {/* Overlay with spotlight */}
      <div className="absolute inset-0 bg-black/50">
        {/* Spotlight cutout */}
        <div
          className="absolute bg-transparent"
          style={{
            left: targetRect.left - 8,
            top: targetRect.top - 8,
            width: targetRect.width + 16,
            height: targetRect.height + 16,
            borderRadius: 8,
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.5)',
          }}
        />
      </div>

      {/* Tooltip */}
      <div
        className={clsx(
          'absolute w-80 p-5 rounded-xl shadow-2xl',
          'bg-white dark:bg-secondary-800',
          'border border-secondary-200 dark:border-secondary-700',
          'animate-fade-in'
        )}
        style={{
          left: tooltipPosition.x,
          top: tooltipPosition.y,
        }}
      >
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-primary-100 dark:bg-primary-900/30 rounded-lg flex items-center justify-center">
              <Sparkles size={16} className="text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="font-semibold text-secondary-900 dark:text-white">{step.title}</h3>
          </div>
          <button
            onClick={handleSkip}
            className="text-secondary-400 hover:text-secondary-600 dark:hover:text-secondary-300"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content */}
        <p className="text-sm text-secondary-600 dark:text-secondary-300 mb-4">{step.content}</p>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-secondary-400 dark:text-secondary-500">
            {currentStep + 1} / {steps.length}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSkip}
              className="flex items-center gap-1 text-sm text-secondary-500 dark:text-secondary-400 hover:text-secondary-700 dark:hover:text-secondary-300"
            >
              <SkipForward size={14} />
              {t('tour.skip', 'Skip')}
            </button>
            {currentStep > 0 && (
              <button
                onClick={handlePrev}
                className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-secondary-600 dark:text-secondary-300 hover:bg-secondary-100 dark:hover:bg-secondary-700 rounded-lg"
              >
                <ChevronLeft size={16} />
                {t('tour.back', 'Back')}
              </button>
            )}
            <button
              onClick={handleNext}
              className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg"
            >
              {currentStep === steps.length - 1 ? t('tour.finish', 'Finish') : t('tour.next', 'Next')}
              {currentStep < steps.length - 1 && <ChevronRight size={16} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Welcome modal for first-time users
interface WelcomeModalProps {
  isOpen: boolean
  onClose: () => void
  onStartTour: () => void
}

export function WelcomeModal({ isOpen, onClose, onStartTour }: WelcomeModalProps) {
  const { t } = useTranslation()

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-secondary-800 rounded-2xl shadow-2xl max-w-md w-full p-6 animate-scale-in">
        <div className="text-center">
          <div className="w-16 h-16 bg-gradient-to-br from-primary-500 to-purple-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Sparkles size={32} className="text-white" />
          </div>
          <h2 className="text-xl font-bold text-secondary-900 dark:text-white mb-2">
            {t('welcome.title', 'Welcome to USMSB!')}
          </h2>
          <p className="text-secondary-600 dark:text-secondary-400 mb-6">
            {t('welcome.description', 'Let us guide you through the key features to get started quickly.')}
          </p>
          <div className="space-y-3">
            <button
              onClick={() => {
                onStartTour()
                onClose()
              }}
              className="w-full btn btn-primary py-3"
            >
              {t('welcome.startTour', 'Start Guided Tour')}
            </button>
            <button
              onClick={onClose}
              className="w-full text-sm text-secondary-500 dark:text-secondary-400 hover:text-secondary-700 dark:hover:text-secondary-300"
            >
              {t('welcome.skipForNow', 'Skip for now')}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
