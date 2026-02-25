import { ReactNode } from 'react'
import clsx from 'clsx'
import { SlideProps } from '../types'

interface SlideContainerProps extends SlideProps {
  children: ReactNode
  className?: string
}

export function SlideContainer({
  children,
  isActive,
  direction,
  className,
}: SlideContainerProps) {
  const getAnimationClass = () => {
    if (!isActive) {
      if (direction === 'left') {
        return 'translate-x-full opacity-0'
      } else if (direction === 'right') {
        return '-translate-x-full opacity-0'
      }
      return 'opacity-0 pointer-events-none'
    }
    return 'translate-x-0 opacity-100'
  }

  return (
    <div
      className={clsx(
        'absolute inset-0 flex items-center justify-center',
        'transition-all duration-500 ease-out',
        getAnimationClass(),
        isActive ? 'z-10' : 'z-0',
        className
      )}
    >
      <div className="w-full h-full overflow-y-auto overflow-x-hidden">
        <div className="min-h-full flex items-center justify-center px-4 py-16 md:py-20 lg:py-24">
          <div className="w-full max-w-6xl mx-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}

export function AnimatedBackground() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none">
      <div className="absolute inset-0 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950" />
      
      <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-primary-500/10 rounded-full blur-[128px] animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-purple-500/10 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: '1s' }} />
      <div className="absolute top-1/2 left-1/2 w-[500px] h-[500px] bg-cyan-500/5 rounded-full blur-[128px] animate-pulse" style={{ animationDelay: '2s' }} />
      
      <div className="absolute inset-0 bg-[linear-gradient(rgba(0,245,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,245,255,0.02)_1px,transparent_1px)] bg-[size:50px_50px]" />
    </div>
  )
}

interface SlideTitleProps {
  children: ReactNode
  subtitle?: ReactNode
  align?: 'left' | 'center' | 'right'
}

export function SlideTitle({ children, subtitle, align = 'center' }: SlideTitleProps) {
  return (
    <div className={clsx('mb-8 md:mb-12', `text-${align}`)}>
      <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold mb-4 font-['Orbitron']">
        <span className="bg-gradient-to-r from-primary-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
          {children}
        </span>
      </h1>
      {subtitle && (
        <p className="text-lg md:text-xl text-slate-400 max-w-3xl mx-auto">
          {subtitle}
        </p>
      )}
    </div>
  )
}

interface SlideContentProps {
  children: ReactNode
  className?: string
}

export function SlideContent({ children, className }: SlideContentProps) {
  return (
    <div className={clsx('text-white', className)}>
      {children}
    </div>
  )
}

interface StatCardProps {
  value: string
  label: string
  icon?: ReactNode
}

export function StatCard({ value, label, icon }: StatCardProps) {
  return (
    <div className="flex flex-col items-center p-6 rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 hover:border-primary-400/30 transition-all">
      {icon && <div className="mb-3 text-primary-400">{icon}</div>}
      <span className="text-3xl md:text-4xl font-bold text-primary-400 mb-2 font-['Orbitron']">{value}</span>
      <span className="text-sm text-slate-400">{label}</span>
    </div>
  )
}

interface FeatureCardProps {
  title: string
  description: string
  icon?: ReactNode
  highlight?: boolean
}

export function FeatureCard({ title, description, icon, highlight }: FeatureCardProps) {
  return (
    <div className={clsx(
      'p-6 rounded-2xl border transition-all',
      highlight
        ? 'bg-gradient-to-br from-primary-500/20 to-purple-500/20 border-primary-400/30'
        : 'bg-white/5 border-white/10 hover:border-white/20'
    )}>
      {icon && <div className="mb-4 text-primary-400">{icon}</div>}
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-slate-400 text-sm">{description}</p>
    </div>
  )
}

interface TokenAllocationProps {
  items: { label: string; percentage: number; color: string }[]
}

export function TokenAllocation({ items }: TokenAllocationProps) {
  return (
    <div className="space-y-4">
      {items.map((item, index) => (
        <div key={index} className="flex items-center gap-4">
          <div className={clsx('w-4 h-4 rounded', item.color)} />
          <span className="flex-1 text-slate-300">{item.label}</span>
          <span className="font-mono text-primary-400">{item.percentage}%</span>
          <div className="w-32 h-2 bg-white/10 rounded-full overflow-hidden">
            <div
              className={clsx('h-full rounded-full', item.color)}
              style={{ width: `${item.percentage}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
