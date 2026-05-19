// AdminFilter.tsx - 通用管理筛选器
import { Search, X } from 'lucide-react'

interface FilterOption {
  label: string
  value: string
}

interface AdminFilterProps {
  searchPlaceholder?: string
  searchValue: string
  onSearchChange: (v: string) => void
  filters?: Array<{
    key: string
    label: string
    options: FilterOption[]
    value: string
    onChange: (v: string) => void
  }>
  className?: string
}

export default function AdminFilter({
  searchPlaceholder = '搜索...',
  searchValue,
  onSearchChange,
  filters = [],
  className = '',
}: AdminFilterProps) {
  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {/* 搜索框 */}
      <div className="relative flex-1 min-w-[200px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={e => onSearchChange(e.target.value)}
          className="w-full bg-bg-tertiary text-text-primary border border-border-primary rounded-lg pl-9 pr-8 py-2 text-sm outline-none placeholder-text-muted focus:border-primary transition-colors"
        />
        {searchValue && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* 筛选下拉 */}
      {filters.map(filter => (
        <select
          key={filter.key}
          value={filter.value}
          onChange={e => filter.onChange(e.target.value)}
          className="bg-bg-tertiary text-text-primary border border-border-primary rounded-lg px-3 py-2 text-sm outline-none min-w-[120px]"
        >
          <option value="">{filter.label}</option>
          {filter.options.map(opt => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      ))}
    </div>
  )
}
