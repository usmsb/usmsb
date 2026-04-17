import { forwardRef } from 'react'
import clsx from 'clsx'

interface Props extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'prefix'> {
  label?: string
  error?: string
  prefixIcon?: React.ReactNode
}

const CyberInput = forwardRef<HTMLInputElement, Props>(
  ({ label, error, prefixIcon, className = '', ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-rajdhani text-text-secondary uppercase tracking-wider mb-1.5">
            {label}
          </label>
        )}
        <div className="relative">
          {prefixIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary pointer-events-none">
              {prefixIcon}
            </span>
          )}
          <input
            ref={ref}
          className={clsx(
            'cyber-input',
            prefixIcon ? 'pl-9' : '',
            error ? 'border-neon-red' : '',
            className
          )}
            {...props}
          />
        </div>
        {error && <p className="mt-1 text-xs text-neon-red font-rajdhani">{error}</p>}
      </div>
    )
  }
)
CyberInput.displayName = 'CyberInput'
export default CyberInput
