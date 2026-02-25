import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { AnimatedBackground } from './components/SlideContainer'
import { SlideNavigation, SlideProgress } from './components/SlideNavigation'
import { useSlideNavigation, useKeyboardControl, useTouchGesture } from './hooks/useSlideNavigation'
import { X, Home } from 'lucide-react'

import { CoverSlide } from './slides/CoverSlide'
import { VisionSlide } from './slides/VisionSlide'
import { ProblemSlide } from './slides/ProblemSlide'
import { SolutionSlide } from './slides/SolutionSlide'
import { TokenEconomicsSlide } from './slides/TokenEconomicsSlide'
import { AgentWalletSlide } from './slides/AgentWalletSlide'
import { AgentFinanceSlide } from './slides/AgentFinanceSlide'
import { ArchitectureSlide } from './slides/ArchitectureSlide'
import { GovernanceSlide } from './slides/GovernanceSlide'
import { RoadmapSlide } from './slides/RoadmapSlide'
import { ParticipationSlide } from './slides/ParticipationSlide'
import { CtaSlide } from './slides/CtaSlide'

const slides = [
  { id: 'cover', component: CoverSlide },
  { id: 'vision', component: VisionSlide },
  { id: 'problem', component: ProblemSlide },
  { id: 'solution', component: SolutionSlide },
  { id: 'token', component: TokenEconomicsSlide },
  { id: 'wallet', component: AgentWalletSlide },
  { id: 'finance', component: AgentFinanceSlide },
  { id: 'architecture', component: ArchitectureSlide },
  { id: 'governance', component: GovernanceSlide },
  { id: 'roadmap', component: RoadmapSlide },
  { id: 'participation', component: ParticipationSlide },
  { id: 'cta', component: CtaSlide },
]

export default function PitchPage() {
  const {
    currentSlide,
    totalSlides,
    direction,
    goToSlide,
    nextSlide,
    prevSlide,
    isFirstSlide,
    isLastSlide,
  } = useSlideNavigation(slides.length)

  useKeyboardControl(nextSlide, prevSlide)
  useTouchGesture(nextSlide, prevSlide)

  useEffect(() => {
    const handleGoToSlide = (e: CustomEvent) => {
      goToSlide(e.detail)
    }
    const handleGoToLastSlide = () => {
      goToSlide(slides.length - 1)
    }

    window.addEventListener('go-to-slide', handleGoToSlide as EventListener)
    window.addEventListener('go-to-last-slide', handleGoToLastSlide)

    return () => {
      window.removeEventListener('go-to-slide', handleGoToSlide as EventListener)
      window.removeEventListener('go-to-last-slide', handleGoToLastSlide)
    }
  }, [goToSlide])

  return (
    <div className="fixed inset-0 overflow-hidden bg-slate-950 text-white">
      <AnimatedBackground />

      <SlideProgress currentSlide={currentSlide} totalSlides={totalSlides} />

      <div className="fixed top-4 right-4 z-50 flex items-center gap-2">
        <Link
          to="/"
          className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-all text-sm"
        >
          <Home className="w-4 h-4" />
          <span className="hidden sm:inline">Home</span>
        </Link>
        <Link
          to="/"
          className="p-2 rounded-lg bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-all"
        >
          <X className="w-4 h-4" />
        </Link>
      </div>

      <div className="relative w-full h-full">
        {slides.map((slide, index) => {
          const SlideComponent = slide.component
          return (
            <SlideComponent
              key={slide.id}
              isActive={index === currentSlide}
              direction={index === currentSlide ? direction : index < currentSlide ? 'right' : 'left'}
            />
          )
        })}
      </div>

      <SlideNavigation
        currentSlide={currentSlide}
        totalSlides={totalSlides}
        onPrev={prevSlide}
        onNext={nextSlide}
        onGoTo={goToSlide}
        isFirstSlide={isFirstSlide}
        isLastSlide={isLastSlide}
      />

      <div className="fixed bottom-20 left-4 text-xs text-white/30 hidden md:block">
        <p>← → Arrow keys to navigate</p>
        <p>Space for next slide</p>
      </div>
    </div>
  )
}
