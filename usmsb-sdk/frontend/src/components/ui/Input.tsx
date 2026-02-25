import { InputHTMLAttributes, forwardRef, useId } from 'react'
import clsx from 'clsx'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  status?: 'default' | 'error' | 'success'
  errorMessage?: string
}

const statusStyles = {
  default: clsx(
    'border-light-border bg-white text-light-text-primary',
    'focus:ring-primary-500 focus:border-primary-500',
    // Cyberpunk dark mode
    'dark:border-neon-blue/30 dark:bg-cyber-dark/80 dark:text-gray-100',
    'dark:focus:border-neon-blue dark:focus:ring-neon-blue/30',
    'dark:focus:shadow-[0_0_15px_rgba(0,245,255,0.2),inset_0_0_10px_rgba(0,245,255,0.05)]'
  ),
  error: clsx(
    'border-red-500 bg-white text-light-text-primary',
    'focus:ring-red-500 focus:border-red-500',
    // Cyberpunk dark mode
    'dark:border-neon-pink dark:bg-cyber-dark/80 dark:text-gray-100',
    'dark:focus:border-neon-pink dark:focus:ring-neon-pink/30',
    'dark:focus:shadow-[0_0_15px_rgba(255,0,170,0.2)]',
    'dark:shadow-[0_0_10px_rgba(255,0,170,0.2)]'
  ),
  success: clsx(
    'border-green-500 bg-white text-light-text-primary',
    'focus:ring-green-500 focus:border-green-500',
    // Cyberpunk dark mode
    'dark:border-neon-green dark:bg-cyber-dark/80 dark:text-gray-100',
    'dark:focus:border-neon-green dark:focus:ring-neon-green/30',
    'dark:focus:shadow-[0_0_15px_rgba(0,255,136,0.2)]',
    'dark:shadow-[0_0_10px_rgba(0,255,136,0.2)]'
  ),
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ status = 'default', errorMessage, className = '', id, ...props }, ref) => {
    const generatedId = useId()
    const inputId = id || generatedId
    const errorId = `${inputId}-error`

    return (
      <div className="w-full">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={status === 'error'}
          aria-describedby={errorMessage ? errorId : undefined}
          className={clsx(
            'w-full px-4 py-3 border rounded-lg',
            'focus:outline-none focus:ring-2',
            'transition-all duration-300',
            // Placeholder styles
            'placeholder:text-light-text-muted',
            'dark:placeholder:text-neon-blue/40 dark:placeholder:font-mono',
            // Cyberpunk font
            'dark:font-mono dark:text-sm',
            statusStyles[status],
            className
          )}
          {...props}
        />
        {errorMessage && (
          <p
            id={errorId}
            role="alert"
            className={clsx(
              'mt-1 text-sm',
              'text-red-500',
              'dark:text-neon-pink dark:font-mono'
            )}
          >
            {errorMessage}
          </p>
        )}
      </div>
    )
  }
)

Input.displayName = 'Input'
