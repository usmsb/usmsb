// utils/export.ts - CSV/Excel 导出工具

/**
 * 通用 CSV 导出函数
 * @param data 数组对象
 * @param filename 文件名（不含扩展名）
 * @param columns 列配置 { key: string, label: string }
 */
export function exportToCSV<T extends Record<string, unknown>>(
  data: T[],
  filename: string,
  columns: Array<{ key: keyof T; label: string; format?: (value: T[keyof T], row: T) => string }>
) {
  if (!data.length) return

  const header = columns.map(c => `"${c.label}"`).join(',')
  const rows = data.map(row =>
    columns.map(col => {
      const raw = row[col.key]
      const val = col.format ? col.format(raw, row) : String(raw ?? '')
      return `"${val.replace(/"/g, '""')}"`
    }).join(',')
  )

  const csv = [header, ...rows].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

/**
 * 格式化导出字段
 */
export const EXPORT_COLUMNS = {
  transactions: [
    { key: 'tx_hash', label: '交易哈希' },
    { key: 'type', label: '类型' },
    { key: 'amount', label: '金额' },
    { key: 'from_address', label: '发送方' },
    { key: 'to_address', label: '接收方' },
    { key: 'status', label: '状态' },
    { key: 'created_at', label: '时间', format: (v: unknown) => v ? new Date((v as number) * 1000).toLocaleString('zh-CN') : '-' },
  ],
  orders: [
    { key: 'order_id', label: '订单ID' },
    { key: 'type', label: '类型' },
    { key: 'status', label: '状态' },
    { key: 'amount', label: '金额' },
    { key: 'agent_id', label: 'Agent' },
    { key: 'created_at', label: '创建时间', format: (v: unknown) => v ? new Date((v as number) * 1000).toLocaleString('zh-CN') : '-' },
  ],
  agents: [
    { key: 'agent_id', label: 'Agent ID' },
    { key: 'name', label: '名称' },
    { key: 'status', label: '状态' },
    { key: 'stake', label: '质押量' },
    { key: 'balance', label: '余额' },
    { key: 'reputation', label: '信誉', format: (v: unknown) => `${((v as number) * 100).toFixed(1)}%` },
  ],
  users: [
    { key: 'user_id', label: '用户ID' },
    { key: 'wallet_address', label: '钱包地址' },
    { key: 'role', label: '角色' },
    { key: 'created_at', label: '注册时间', format: (v: unknown) => v ? new Date((v as number) * 1000).toLocaleString('zh-CN') : '-' },
  ],
}
