export interface SlideProps {
  isActive: boolean
  direction: 'left' | 'right' | 'none'
}

export interface SlideConfig {
  id: string
  component: React.ComponentType<SlideProps>
  title: string
  description: string
}

export interface PitchContextType {
  currentSlide: number
  totalSlides: number
  direction: 'left' | 'right' | 'none'
  isAnimating: boolean
  goToSlide: (index: number) => void
  nextSlide: () => void
  prevSlide: () => void
  isFirstSlide: boolean
  isLastSlide: boolean
}

export interface DappExtensionState {
  isConnected: boolean
  address: string | null
  balance: string
  stakedAmount: string
  stakeTier: string
}

export interface TouchState {
  startX: number
  startY: number
  isDragging: boolean
}
