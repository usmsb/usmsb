import { useTranslation } from 'react-i18next'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import clsx from 'clsx'

interface SlideNavigationProps {
  currentSlide: number
  totalSlides: number
  onPrev: () => void
  onNext: () => void
  onGoTo: (index: number) => void
  isFirstSlide: boolean
  isLastSlide: boolean
}

export function SlideNavigation({
  currentSlide,
  totalSlides,
  onPrev,
  onNext,
  onGoTo,
  isFirstSlide,
  isLastSlide,
}: SlideNavigationProps) {
  const { t } = useTranslation()

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-gradient-to-t from-black/50 to-transparent py-4 px-4 md:py-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <button
          onClick={onPrev}
          disabled={isFirstSlide}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-all',
            'bg-white/10 backdrop-blur-sm border border-white/20',
            'hover:bg-white/20 hover:border-white/30',
            'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-white/10'
          )}
        >
          <ChevronLeft className="w-5 h-5" />
          <span className="hidden sm:inline">{t('common.previous')}</span>
        </button>

        <div className="flex items-center gap-2">
          {Array.from({ length: totalSlides }).map((_, index) => (
            <button
              key={index}
              onClick={() => onGoTo(index)}
              className={clsx(
                'transition-all duration-300',
                'w-2 h-2 md:w-3 md:h-3 rounded-full',
                index === currentSlide
                  ? 'bg-primary-400 scale-125 shadow-lg shadow-primary-400/50'
                  : 'bg-white/30 hover:bg-white/50'
              )}
            />
          ))}
        </div>

        <button
          onClick={onNext}
          disabled={isLastSlide}
          className={clsx(
            'flex items-center gap-2 px-4 py-2 rounded-lg transition-all',
            'bg-white/10 backdrop-blur-sm border border-white/20',
            'hover:bg-white/20 hover:border-white/30',
            'disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-white/10'
          )}
        >
          <span className="hidden sm:inline">{t('common.next')}</span>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      <div className="text-center mt-2 text-xs text-white/50">
        {currentSlide + 1} / {totalSlides}
      </div>
    </div>
  )
}

interface SlideProgressProps {
  currentSlide: number
  totalSlides: number
}

export function SlideProgress({ currentSlide, totalSlides }: SlideProgressProps) {
  const progress = ((currentSlide + 1) / totalSlides) * 100

  return (
    <div className="fixed top-0 left-0 right-0 z-50 h-1 bg-white/10">
      <div
        className="h-full bg-gradient-to-r from-primary-500 to-purple-500 transition-all duration-500"
        style={{ width: `${progress}%` }}
      />
    </div>
  )
}
