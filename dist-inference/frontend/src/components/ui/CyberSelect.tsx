import { forwardRef } from 'react'
import clsx from 'clsx'

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
}

const CyberSelect = forwardRef<HTMLSelectElement, SelectProps>(
  ({ label, error, className = '', children, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label className="block text-xs font-rajdhani text-text-secondary uppercase tracking-wider mb-1.5">
            {label}
          </label>
        )}
        <select
          ref={ref}
          className={clsx(
            'cyber-input appearance-none cursor-pointer',
            error ? 'border-neon-red' : '',
            className
          )}
          {...props}
        >
          {children}
        </select>
        {error && <p className="mt-1 text-xs text-neon-red font-rajdhani">{error}</p>}
      </div>
    )
  }
)
CyberSelect.displayName = 'CyberSelect'
export default CyberSelect
