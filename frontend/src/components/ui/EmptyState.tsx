import { LucideIcon, FolderOpen, Search, PlusCircle } from 'lucide-react'
import clsx from 'clsx'
import { Button } from './Button'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    icon?: LucideIcon
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  className?: string
  illustration?: 'empty' | 'search' | 'create'
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className,
  illustration = 'empty',
}: EmptyStateProps) {
  // Default icons based on illustration type
  const DefaultIcon = illustration === 'search' ? Search : illustration === 'create' ? PlusCircle : FolderOpen

  return (
    <div className={clsx(
      'flex flex-col items-center justify-center py-12 px-4 text-center',
      className
    )}>
      {/* Illustration */}
      <div className="relative mb-6">
        <div className={clsx(
          'w-20 h-20 rounded-full flex items-center justify-center',
          'bg-light-bg-tertiary dark:bg-secondary-800'
        )}>
          {Icon ? (
            <Icon className="w-10 h-10 text-light-text-muted dark:text-secondary-500" />
          ) : (
            <DefaultIcon className="w-10 h-10 text-light-text-muted dark:text-secondary-500" />
          )}
        </div>
        {/* Decorative elements */}
        <div className="absolute -top-1 -right-1 w-6 h-6 bg-primary-100 dark:bg-primary-900/30 rounded-full animate-pulse" />
        <div className="absolute -bottom-2 -left-2 w-4 h-4 bg-purple-100 dark:bg-purple-900/30 rounded-full animate-pulse delay-150" />
      </div>

      {/* Text content */}
      <h3 className="text-lg font-semibold text-light-text-primary dark:text-secondary-100 mb-2">
        {title}
      </h3>
      {description && (
        <p className="text-light-text-muted dark:text-secondary-400 max-w-sm mb-6">
          {description}
        </p>
      )}

      {/* Actions */}
      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center gap-3">
          {action && (
            <Button
              onClick={action.onClick}
              className="flex items-center gap-2"
            >
              {action.icon && <action.icon size={18} />}
              {action.label}
            </Button>
          )}
          {secondaryAction && (
            <button
              onClick={secondaryAction.onClick}
              className="text-sm text-light-text-secondary dark:text-secondary-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors"
            >
              {secondaryAction.label}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Loading skeleton for cards
export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div className={clsx(
      'card animate-pulse',
      className
    )}>
      <div className="flex items-center justify-between mb-4">
        <div className="h-4 bg-secondary-200 dark:bg-secondary-700 rounded w-1/3" />
        <div className="h-10 w-10 bg-secondary-200 dark:bg-secondary-700 rounded-xl" />
      </div>
      <div className="h-8 bg-secondary-200 dark:bg-secondary-700 rounded w-1/2 mb-4" />
      <div className="flex items-center gap-2">
        <div className="h-4 w-4 bg-secondary-200 dark:bg-secondary-700 rounded" />
        <div className="h-4 bg-secondary-200 dark:bg-secondary-700 rounded w-20" />
      </div>
    </div>
  )
}

// List item skeleton
export function ListItemSkeleton({ className }: { className?: string }) {
  return (
    <div className={clsx(
      'flex items-center gap-4 p-4 rounded-lg bg-light-bg-tertiary dark:bg-secondary-800/50 animate-pulse',
      className
    )}>
      <div className="w-10 h-10 bg-secondary-200 dark:bg-secondary-700 rounded-full" />
      <div className="flex-1">
        <div className="h-4 bg-secondary-200 dark:bg-secondary-700 rounded w-1/3 mb-2" />
        <div className="h-3 bg-secondary-200 dark:bg-secondary-700 rounded w-1/2" />
      </div>
      <div className="text-right">
        <div className="h-4 bg-secondary-200 dark:bg-secondary-700 rounded w-16 mb-2" />
        <div className="h-3 bg-secondary-200 dark:bg-secondary-700 rounded w-12" />
      </div>
    </div>
  )
}
