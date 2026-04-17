import { forwardRef } from 'react'
import clsx from 'clsx'
import { Loader2 } from 'lucide-react'

interface Props extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
}

const CyberButton = forwardRef<HTMLButtonElement, Props>(
  ({ variant = 'primary', size = 'md', loading, children, className = '', disabled, ...props }, ref) => {
    const variantClass = {
      primary: 'cyber-btn-primary',
      secondary: 'cyber-btn-secondary',
      ghost: 'cyber-btn-ghost',
      danger: 'border-neon-red text-neon-red hover:bg-neon-red/10',
    }[variant]

    const sizeClass = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-5 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    }[size]

    return (
      <button
        ref={ref}
        className={clsx('cyber-btn', variantClass, sizeClass, loading && 'opacity-70 cursor-not-allowed', className)}
        disabled={disabled || loading}
        {...props}
      >
        {loading && <Loader2 size={14} className="animate-spin" />}
        {children}
      </button>
    )
  }
)
CyberButton.displayName = 'CyberButton'
export default CyberButton
