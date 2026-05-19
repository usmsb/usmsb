// VoteBar.tsx - 投票进度条
import { ThumbsUp, ThumbsDown } from 'lucide-react'

interface VoteBarProps {
  forVotes: number
  againstVotes: number
  showLabels?: boolean
  className?: string
}

export default function VoteBar({
  forVotes,
  againstVotes,
  showLabels = true,
  className = '',
}: VoteBarProps) {
  const total = forVotes + againstVotes || 1
  const forPct = (forVotes / total) * 100
  const againstPct = (againstVotes / total) * 100

  return (
    <div className={`space-y-1 ${className}`}>
      {showLabels && (
        <div className="flex justify-between text-xs px-1">
          <span className="text-success flex items-center gap-1">
            <ThumbsUp className="w-3 h-3" />
            {forVotes.toLocaleString()} ({forPct.toFixed(1)}%)
          </span>
          <span className="text-danger flex items-center gap-1">
            <ThumbsDown className="w-3 h-3" />
            {againstVotes.toLocaleString()} ({againstPct.toFixed(1)}%)
          </span>
        </div>
      )}
      <div className="flex h-2.5 rounded-full overflow-hidden bg-danger/30">
        <div
          className="h-full bg-success transition-all duration-500"
          style={{ width: `${forPct}%` }}
        />
      </div>
    </div>
  )
}
