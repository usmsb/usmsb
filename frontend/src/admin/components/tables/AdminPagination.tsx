// AdminPagination.tsx - 通用分页组件
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

interface AdminPaginationProps {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  className?: string
}

export default function AdminPagination({
  page,
  pageSize,
  total,
  onPageChange,
  className = '',
}: AdminPaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const pages = Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
    if (totalPages <= 7) return i + 1
    if (page <= 4) return i + 1
    if (page >= totalPages - 3) return totalPages - 6 + i
    return page - 3 + i
  })

  return (
    <div className={`flex items-center justify-between px-4 py-3 ${className}`}>
      <span className="text-text-muted text-sm">
        第 <span className="font-mono text-text-primary">{page}</span> /{' '}
        <span className="font-mono">{totalPages}</span> 页，共{' '}
        <span className="font-mono">{total}</span> 条
      </span>

      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <ChevronsLeft className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="p-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {pages.map(p => (
          <button
            key={p}
            onClick={() => onPageChange(p)}
            className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
              p === page
                ? 'bg-primary text-white'
                : 'bg-bg-tertiary text-text-secondary hover:text-text-primary'
            }`}
          >
            {p}
          </button>
        ))}

        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          className="p-1.5 rounded-lg bg-bg-tertiary text-text-secondary hover:text-text-primary disabled:opacity-30 transition-colors"
        >
          <ChevronsRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
