import { useState, useCallback, useEffect } from 'react'

export function useSlideNavigation(totalSlides: number) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [direction, setDirection] = useState<'left' | 'right' | 'none'>('none')
  const [isAnimating, setIsAnimating] = useState(false)

  const goToSlide = useCallback((index: number) => {
    if (isAnimating) return
    if (index < 0 || index >= totalSlides) return
    if (index === currentSlide) return

    setDirection(index > currentSlide ? 'left' : 'right')
    setIsAnimating(true)
    setCurrentSlide(index)

    setTimeout(() => {
      setIsAnimating(false)
      setDirection('none')
    }, 500)
  }, [currentSlide, totalSlides, isAnimating])

  const nextSlide = useCallback(() => {
    if (currentSlide < totalSlides - 1) {
      goToSlide(currentSlide + 1)
    }
  }, [currentSlide, totalSlides, goToSlide])

  const prevSlide = useCallback(() => {
    if (currentSlide > 0) {
      goToSlide(currentSlide - 1)
    }
  }, [currentSlide, goToSlide])

  return {
    currentSlide,
    totalSlides,
    direction,
    isAnimating,
    goToSlide,
    nextSlide,
    prevSlide,
    isFirstSlide: currentSlide === 0,
    isLastSlide: currentSlide === totalSlides - 1,
  }
}

export function useKeyboardControl(
  nextSlide: () => void,
  prevSlide: () => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      switch (e.key) {
        case 'ArrowRight':
        case 'ArrowDown':
        case ' ':
        case 'PageDown':
          e.preventDefault()
          nextSlide()
          break
        case 'ArrowLeft':
        case 'ArrowUp':
        case 'PageUp':
          e.preventDefault()
          prevSlide()
          break
        case 'Home':
          e.preventDefault()
          window.dispatchEvent(new CustomEvent('go-to-slide', { detail: 0 }))
          break
        case 'End':
          e.preventDefault()
          window.dispatchEvent(new CustomEvent('go-to-last-slide'))
          break
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [nextSlide, prevSlide, enabled])
}

export function useTouchGesture(
  nextSlide: () => void,
  prevSlide: () => void,
  enabled: boolean = true
) {
  useEffect(() => {
    if (!enabled) return

    let startX = 0
    let startY = 0
    let isDragging = false

    const handleTouchStart = (e: TouchEvent) => {
      startX = e.touches[0].clientX
      startY = e.touches[0].clientY
      isDragging = true
    }

    const handleTouchEnd = (e: TouchEvent) => {
      if (!isDragging) return
      isDragging = false

      const endX = e.changedTouches[0].clientX
      const endY = e.changedTouches[0].clientY
      const diffX = endX - startX
      const diffY = endY - startY

      const minSwipeDistance = 50

      if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > minSwipeDistance) {
        if (diffX < 0) {
          nextSlide()
        } else {
          prevSlide()
        }
      }
    }

    const handleTouchMove = (e: TouchEvent) => {
      if (!isDragging) return
      const diffY = e.touches[0].clientY - startY
      if (Math.abs(diffY) > Math.abs(e.touches[0].clientX - startX)) {
        e.preventDefault()
      }
    }

    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchend', handleTouchEnd, { passive: true })
    document.addEventListener('touchmove', handleTouchMove, { passive: false })

    return () => {
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchend', handleTouchEnd)
      document.removeEventListener('touchmove', handleTouchMove)
    }
  }, [nextSlide, prevSlide, enabled])
}
