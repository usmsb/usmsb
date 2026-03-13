import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import {
  X,
  Sparkles,
  Users,
  Target,
  Zap,
  Rocket,
  ChevronRight,
  ChevronLeft,
  Trophy,
} from 'lucide-react'
import clsx from 'clsx'
import { Button } from './ui/Button'

interface GuideStep {
  id: number
  titleKey: string
  descKey: string
  icon: React.ElementType
  color: string
  feature?: string
}

const guideSteps: GuideStep[] = [
  {
    id: 1,
    titleKey: 'guide.welcome.title',
    descKey: 'guide.welcome.desc',
    icon: Sparkles,
    color: 'from-purple-500 to-pink-500',
  },
  {
    id: 2,
    titleKey: 'guide.agents.title',
    descKey: 'guide.agents.desc',
    icon: Users,
    color: 'from-blue-500 to-cyan-500',
    feature: '/app/agents',
  },
  {
    id: 3,
    titleKey: 'guide.matching.title',
    descKey: 'guide.matching.desc',
    icon: Target,
    color: 'from-green-500 to-emerald-500',
    feature: '/app/matching',
  },
  {
    id: 4,
    titleKey: 'guide.collaborate.title',
    descKey: 'guide.collaborate.desc',
    icon: Zap,
    color: 'from-orange-500 to-amber-500',
    feature: '/app/collaborations',
  },
  {
    id: 5,
    titleKey: 'guide.explore.title',
    descKey: 'guide.explore.desc',
    icon: Rocket,
    color: 'from-primary-500 to-purple-500',
  },
]

const STORAGE_KEY = 'usmsb_guide_completed'

interface WelcomeGuideProps {
  onComplete?: () => void
}

export function WelcomeGuide({ onComplete }: WelcomeGuideProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    // Check if guide has been completed before
    const completed = localStorage.getItem(STORAGE_KEY)
    if (!completed) {
      // Small delay for better UX
      const timer = setTimeout(() => setIsOpen(true), 1000)
      return () => clearTimeout(timer)
    }
  }, [])

  const handleClose = () => {
    setIsOpen(false)
    localStorage.setItem(STORAGE_KEY, 'true')
    onComplete?.()
  }

  const handleNext = () => {
    if (currentStep < guideSteps.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      handleClose()
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1)
    }
  }

  const handleSkip = () => {
    handleClose()
  }

  const handleExploreFeature = (path?: string) => {
    handleClose()
    if (path) {
      navigate(path)
    }
  }

  if (!isOpen) return null

  const step = guideSteps[currentStep]
  const isLastStep = currentStep === guideSteps.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in"
        onClick={handleSkip}
      />

      {/* Modal */}
      <div
        className={clsx(
          'relative w-full max-w-lg bg-white dark:bg-cyber-card',
          'rounded-2xl shadow-2xl overflow-hidden animate-scale-in'
        )}
        role="dialog"
        aria-modal="true"
        aria-labelledby="guide-title"
      >
        {/* Close button */}
        <button
          onClick={handleSkip}
          className="absolute top-4 right-4 z-10 p-2 rounded-lg text-secondary-400 hover:text-secondary-600 hover:bg-secondary-100 dark:hover:bg-secondary-800 transition-colors"
          aria-label="Close guide"
        >
          <X size={20} />
        </button>

        {/* Progress bar */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-secondary-100 dark:bg-secondary-800">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-purple-500 transition-all duration-300"
            style={{ width: `${((currentStep + 1) / guideSteps.length) * 100}%` }}
          />
        </div>

        {/* Content */}
        <div className="pt-8 pb-6 px-6">
          {/* Step indicator */}
          <div className="flex justify-center gap-2 mb-6">
            {guideSteps.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentStep(index)}
                className={clsx(
                  'w-2 h-2 rounded-full transition-all duration-300',
                  index === currentStep
                    ? 'w-6 bg-primary-500'
                    : index < currentStep
                    ? 'bg-primary-300 dark:bg-primary-700'
                    : 'bg-secondary-200 dark:bg-secondary-700'
                )}
                aria-label={`Go to step ${index + 1}`}
              />
            ))}
          </div>

          {/* Icon */}
          <div className="flex justify-center mb-6">
            <div
              className={clsx(
                'w-20 h-20 rounded-2xl flex items-center justify-center',
                'bg-gradient-to-br shadow-lg',
                step.color
              )}
            >
              <step.icon className="w-10 h-10 text-white" />
            </div>
          </div>

          {/* Title & Description */}
          <h2
            id="guide-title"
            className="text-2xl font-bold text-center text-secondary-900 dark:text-secondary-100 mb-3"
          >
            {t(step.titleKey)}
          </h2>
          <p className="text-center text-secondary-600 dark:text-secondary-400 mb-6">
            {t(step.descKey)}
          </p>

          {/* Feature card for steps with features */}
          {step.feature && (
            <div
              className={clsx(
                'p-4 rounded-xl border-2 border-dashed',
                'border-secondary-200 dark:border-secondary-700',
                'bg-secondary-50 dark:bg-secondary-800/50',
                'cursor-pointer hover:border-primary-400 dark:hover:border-primary-500',
                'transition-colors group'
              )}
              onClick={() => handleExploreFeature(step.feature)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={clsx(
                    'w-10 h-10 rounded-lg flex items-center justify-center',
                    'bg-gradient-to-br',
                    step.color
                  )}>
                    <step.icon className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <p className="font-medium text-secondary-900 dark:text-secondary-100">
                      {t('guide.tryIt')}
                    </p>
                    <p className="text-sm text-secondary-500 dark:text-secondary-400">
                      {t('guide.clickToExplore')}
                    </p>
                  </div>
                </div>
                <ChevronRight className="w-5 h-5 text-secondary-400 group-hover:text-primary-500 transition-colors" />
              </div>
            </div>
          )}

          {/* Last step - achievements preview */}
          {isLastStep && (
            <div className="flex justify-center gap-4 mt-4">
              <div className="flex items-center gap-2 px-3 py-2 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <Trophy className="w-5 h-5 text-yellow-500" />
                <span className="text-sm text-yellow-700 dark:text-yellow-400">{t('guide.achievements')}</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <Sparkles className="w-5 h-5 text-purple-500" />
                <span className="text-sm text-purple-700 dark:text-purple-400">{t('guide.rewards')}</span>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-secondary-50 dark:bg-secondary-800/50">
          <button
            onClick={handleSkip}
            className="text-sm text-secondary-500 hover:text-secondary-700 dark:text-secondary-400 dark:hover:text-secondary-200 transition-colors"
          >
            {t('guide.skip')}
          </button>

          <div className="flex items-center gap-3">
            {currentStep > 0 && (
              <Button variant="ghost" size="sm" onClick={handlePrev}>
                <ChevronLeft size={16} className="mr-1" />
                {t('common.previous')}
              </Button>
            )}
            <Button size="sm" onClick={handleNext}>
              {isLastStep ? t('guide.getStarted') : t('common.next')}
              {!isLastStep && <ChevronRight size={16} className="ml-1" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

// Hook to check if guide should be shown
export function useShouldShowGuide(): boolean {
  const [shouldShow, setShouldShow] = useState(false)

  useEffect(() => {
    const completed = localStorage.getItem(STORAGE_KEY)
    setShouldShow(!completed)
  }, [])

  return shouldShow
}

// Button to restart guide
export function RestartGuideButton() {
  const { t } = useTranslation()
  const [showGuide, setShowGuide] = useState(false)

  const handleRestart = () => {
    localStorage.removeItem(STORAGE_KEY)
    setShowGuide(true)
  }

  return (
    <>
      <button
        onClick={handleRestart}
        className="flex items-center gap-2 text-sm text-secondary-600 hover:text-primary-600 dark:text-secondary-400 dark:hover:text-primary-400 transition-colors"
      >
        <Rocket size={16} />
        {t('guide.restart')}
      </button>
      {showGuide && <WelcomeGuide onComplete={() => setShowGuide(false)} />}
    </>
  )
}
