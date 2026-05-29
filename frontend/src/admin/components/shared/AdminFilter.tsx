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
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          value={searchValue}
          onChange={e => onSearchChange(e.target.value)}
          className="w-full bg-cyber-dark text-gray-200 border border-neon-blue/30 rounded-lg pl-9 pr-8 py-2 text-sm outline-none placeholder-gray-500 focus:border-neon-blue transition-colors font-cyber"
        />
        {searchValue && (
          <button
            onClick={() => onSearchChange('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-neon-blue"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* 筛选下拉 */}
      {filters.map(filter => (
        <div key={filter.key} className="relative">
          <select
            value={filter.value}
            onChange={e => filter.onChange(e.target.value)}
            className="input appearance-none cursor-pointer pr-8 min-w-[120px]"
          >
            <option value="">{filter.label}</option>
            {filter.options.map(opt => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
            <svg width="10" height="6" viewBox="0 0 10 6" fill="none" className="text-neon-blue">
              <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      ))}
    </div>
  )
}
