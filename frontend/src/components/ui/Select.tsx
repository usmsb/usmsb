import { SelectHTMLAttributes, useId } from 'react'
import clsx from 'clsx'
import { ChevronDown } from 'lucide-react'

interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'children'> {
  label?: string
  options: SelectOption[]
  error?: string
  hint?: string
  className?: string
}

export function Select({
  label,
  options,
  error,
  hint,
  className = '',
  id,
  ...props
}: SelectProps) {
  const generatedId = useId()
  const selectId = id || generatedId
  const errorId = `${selectId}-error`
  const hintId = `${selectId}-hint`

  return (
    <div className={clsx('w-full', className)}>
      {label && (
        <label
          htmlFor={selectId}
          className="block text-sm font-medium text-light-text-secondary dark:text-gray-300 mb-1.5"
        >
          {label}
        </label>
      )}

      <div className="relative">
        <select
          id={selectId}
          className={clsx(
            'w-full appearance-none rounded-lg border bg-white dark:bg-cyber-card',
            'px-4 py-2.5 pr-10 text-light-text-primary dark:text-white',
            'border-light-border dark:border-secondary-700',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'disabled:bg-light-bg-tertiary dark:disabled:bg-secondary-900 disabled:cursor-not-allowed',
            // Cyberpunk dark mode styling
            'dark:shadow-[0_0_10px_rgba(0,245,255,0.1)]',
            'dark:focus:shadow-[0_0_15px_rgba(0,245,255,0.3)]',
            'dark:font-cyber',
            // Error state
            error
              ? 'border-red-500 focus:ring-red-500 dark:border-red-400'
              : 'border-light-border dark:border-neon-blue/30'
          )}
          aria-invalid={error ? 'true' : undefined}
          aria-describedby={
            [error && errorId, hint && hintId].filter(Boolean).join(' ') || undefined
          }
          {...props}
        >
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>

        {/* Custom dropdown icon */}
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          <ChevronDown
            size={18}
            className="text-light-text-muted dark:text-gray-500"
          />
        </div>
      </div>

      {/* Hint text */}
      {hint && !error && (
        <p id={hintId} className="mt-1.5 text-sm text-light-text-muted dark:text-gray-400">
          {hint}
        </p>
      )}

      {/* Error message */}
      {error && (
        <p id={errorId} className="mt-1.5 text-sm text-red-600 dark:text-red-400" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}

export default Select
