import clsx from 'clsx'
import { getStatusBadgeClass } from '@/lib/utils'

interface Props {
  status: string
  label?: string
  dot?: boolean
}

export default function Badge({ status, label, dot }: Props) {
  const cls = getStatusBadgeClass(status)
  const displayLabel = label || status.replace(/_/g, ' ').toUpperCase()

  return (
    <span className={clsx('badge', cls)}>
      {dot && (
        <span
          className={clsx('w-1.5 h-1.5 rounded-full', {
            'bg-neon-green': status === 'idle' || status === 'completed',
            'bg-neon-blue': status === 'busy' || status === 'running',
            'bg-neon-red': status === 'offline' || status === 'failed',
            'bg-neon-yellow': status === 'loading' || status === 'queued',
            'bg-neon-purple': status === 'maintenance',
          })}
        />
      )}
      {displayLabel}
    </span>
  )
}
