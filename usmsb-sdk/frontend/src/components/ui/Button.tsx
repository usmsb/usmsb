import { ButtonHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'warning'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  children: ReactNode
}

const variants = {
  primary: clsx(
    // 浅色模式: 蓝紫渐变 (参考官网)
    'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white',
    // 深色模式: 霓虹风格
    'dark:bg-gradient-to-r dark:from-neon-blue/20 dark:to-neon-purple/20',
    'dark:border dark:border-neon-blue dark:text-neon-blue',
    'dark:hover:from-neon-blue/30 dark:hover:to-neon-purple/30',
    'dark:hover:shadow-[0_0_20px_rgba(0,245,255,0.4),inset_0_0_20px_rgba(0,245,255,0.1)]',
    'dark:hover:text-neon-blue dark:active:shadow-[0_0_10px_rgba(0,245,255,0.3)]'
  ),
  secondary: clsx(
    // 浅色模式: 浅蓝紫背景
    'bg-gradient-to-r from-blue-100 to-purple-100 text-blue-700 hover:from-blue-200 hover:to-purple-200',
    // 深色模式: 霓虹紫
    'dark:bg-neon-purple/10 dark:text-neon-purple dark:border dark:border-neon-purple/50',
    'dark:hover:bg-neon-purple/20 dark:hover:border-neon-purple',
    'dark:hover:shadow-[0_0_15px_rgba(191,0,255,0.3)]'
  ),
  outline: clsx(
    // 浅色模式: 蓝紫色边框
    'border-2 border-blue-500 text-blue-600 hover:from-blue-500 hover:to-purple-600 hover:text-white',
    'hover:bg-gradient-to-r hover:from-blue-500 hover:to-purple-600',
    // 深色模式
    'dark:border-neon-blue/50 dark:text-neon-blue',
    'dark:hover:bg-neon-blue/10 dark:hover:border-neon-blue',
    'dark:hover:shadow-[0_0_15px_rgba(0,245,255,0.3)]'
  ),
  ghost: clsx(
    // 浅色模式: 蓝紫色调
    'text-blue-600 hover:bg-blue-50 active:bg-blue-100',
    'dark:text-gray-400 dark:hover:bg-neon-blue/5 dark:hover:text-neon-blue'
  ),
  danger: clsx(
    // 浅色模式: 红色
    'bg-red-500 text-white hover:bg-red-600 active:bg-red-700',
    // 深色模式: 霓虹粉
    'dark:bg-neon-pink/20 dark:text-neon-pink dark:border dark:border-neon-pink/50',
    'dark:hover:bg-neon-pink/30 dark:hover:border-neon-pink',
    'dark:hover:shadow-[0_0_15px_rgba(255,0,170,0.4)]'
  ),
  success: clsx(
    // 浅色模式: 绿色
    'bg-green-500 text-white hover:bg-green-600 active:bg-green-700',
    // 深色模式: 霓虹绿
    'dark:bg-neon-green/20 dark:text-neon-green dark:border dark:border-neon-green/50',
    'dark:hover:bg-neon-green/30 dark:hover:border-neon-green',
    'dark:hover:shadow-[0_0_15px_rgba(0,255,136,0.4)]'
  ),
  warning: clsx(
    // 浅色模式: 黄色/橙色
    'bg-yellow-500 text-white hover:bg-yellow-600 active:bg-yellow-700',
    // 深色模式: 霓虹黄
    'dark:bg-yellow-500/20 dark:text-yellow-400 dark:border dark:border-yellow-500/50',
    'dark:hover:bg-yellow-500/30 dark:hover:border-yellow-400',
    'dark:hover:shadow-[0_0_15px_rgba(250,204,21,0.4)]'
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
