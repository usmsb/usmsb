import { ButtonHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

const variants = {
  primary: clsx(
    'bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800',
    'dark:bg-gradient-to-r dark:from-neon-blue/20 dark:to-neon-purple/20',
    'dark:border dark:border-neon-blue dark:text-neon-blue',
    'dark:hover:from-neon-blue/30 dark:hover:to-neon-purple/30',
    'dark:hover:shadow-[0_0_20px_rgba(0,245,255,0.4),inset_0_0_20px_rgba(0,245,255,0.1)]',
    'dark:hover:text-neon-blue dark:active:shadow-[0_0_10px_rgba(0,245,255,0.3)]'
  ),
  secondary: clsx(
    'bg-secondary-200 text-secondary-800 hover:bg-secondary-300 active:bg-secondary-400',
    'dark:bg-neon-purple/10 dark:text-neon-purple dark:border dark:border-neon-purple/50',
    'dark:hover:bg-neon-purple/20 dark:hover:border-neon-purple',
    'dark:hover:shadow-[0_0_15px_rgba(191,0,255,0.3)]'
  ),
  outline: clsx(
    'border-2 border-primary-600 text-primary-600 hover:bg-primary-50 active:bg-primary-100',
    'dark:border-neon-blue/50 dark:text-neon-blue',
    'dark:hover:bg-neon-blue/10 dark:hover:border-neon-blue',
    'dark:hover:shadow-[0_0_15px_rgba(0,245,255,0.3)]'
  ),
  ghost: clsx(
    'text-secondary-600 hover:bg-secondary-100 active:bg-secondary-200',
    'dark:text-gray-400 dark:hover:bg-neon-blue/5 dark:hover:text-neon-blue'
  ),
  danger: clsx(
    'bg-red-600 text-white hover:bg-red-700 active:bg-red-800',
    'dark:bg-neon-pink/20 dark:text-neon-pink dark:border dark:border-neon-pink/50',
    'dark:hover:bg-neon-pink/30 dark:hover:border-neon-pink',
    'dark:hover:shadow-[0_0_15px_rgba(255,0,170,0.4)]'
  ),
  success: clsx(
    'bg-green-600 text-white hover:bg-green-700 active:bg-green-800',
    'dark:bg-neon-green/20 dark:text-neon-green dark:border dark:border-neon-green/50',
    'dark:hover:bg-neon-green/30 dark:hover:border-neon-green',
    'dark:hover:shadow-[0_0_15px_rgba(0,255,136,0.4)]'
  ),
}

const sizes = {
  sm: 'px-3 py-1.5 text-sm',
  md: 'px-4 py-2 text-base',
  lg: 'px-6 py-3 text-lg',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled,
  className = '',
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'relative inline-flex items-center justify-center rounded-lg font-medium',
        'transition-all duration-300 focus:outline-none focus:ring-2',
        'focus:ring-primary-500 focus:ring-offset-2 dark:focus:ring-offset-cyber-dark',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none',
        'overflow-hidden',
        // Cyberpunk shine effect on hover
        'dark:before:absolute dark:before:top-0 dark:before:-left-full dark:before:w-full dark:before:h-full',
        'dark:before:bg-gradient-to-r dark:before:from-transparent dark:before:via-white/10 dark:before:to-transparent',
        'dark:before:transition-all dark:before:duration-500',
        'dark:hover:before:left-full',
        'dark:font-cyber dark:tracking-wider dark:uppercase dark:text-sm',
        variants[variant],
        sizes[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <span className="mr-2 inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
      )}
      {children}
    </button>
  )
}
