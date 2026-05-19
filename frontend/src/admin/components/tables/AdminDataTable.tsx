// AdminDataTable.tsx - 通用数据表格
import { ReactNode } from 'react'

export interface Column<T> {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: (row: T, index: number) => ReactNode
}

interface AdminDataTableProps<T extends Record<string, unknown>> {
  columns: Column<T>[]
  data: T[]
  isLoading?: boolean
  loadingRows?: number
  emptyMessage?: string
  onRowClick?: (row: T) => void
  className?: string
}

export default function AdminDataTable<T extends Record<string, unknown>>({
  columns,
  data,
  isLoading,
  loadingRows = 5,
  emptyMessage = '暂无数据',
  onRowClick,
  className = '',
}: AdminDataTableProps<T>) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border-primary bg-bg-tertiary">
            {columns.map(col => (
              <th
                key={col.key}
                className={`px-4 py-3 text-text-muted font-normal whitespace-nowrap ${
                  col.align === 'right' ? 'text-right' :
                  col.align === 'center' ? 'text-center' : 'text-left'
                }`}
                style={{ width: col.width }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {isLoading ? (
            [...Array(loadingRows)].map((_, i) => (
              <tr key={i} className="border-b border-border-primary/50">
                {columns.map(col => (
                  <td key={col.key} className="px-4 py-3">
                    <div className="h-4 bg-bg-tertiary rounded animate-pulse" />
                  </td>
                ))}
              </tr>
            ))
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="text-center text-text-muted py-12">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-border-primary/50 transition-colors ${
                  onRowClick ? 'cursor-pointer hover:bg-bg-tertiary/50' : ''
                }`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(col => (
                  <td
                    key={col.key}
                    className={`px-4 py-3 ${
                      col.align === 'right' ? 'text-right' :
                      col.align === 'center' ? 'text-center' : 'text-left'
                    }`}
                  >
                    {col.render ? col.render(row, i) : String(row[col.key] ?? '-')}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
