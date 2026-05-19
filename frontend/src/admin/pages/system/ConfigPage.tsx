/** ConfigPage - 运行时配置 */
import { useQuery } from '@tanstack/react-query'
import { fetchSystemConfig } from '../../api/adminApi'

export default function ConfigPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'system', 'config'],
    queryFn: fetchSystemConfig,
    refetchInterval: 120000,
  })

  const config = data ?? {}

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">运行时配置</h1>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <div className="px-4 py-3 border-b border-border-primary bg-bg-tertiary">
          <h3 className="text-text-primary font-rajdhani font-semibold">当前配置</h3>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {isLoading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i} className="border-b border-border-primary/50">
                  <td className="px-4 py-3"><div className="h-4 w-24 bg-bg-tertiary rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-48 bg-bg-tertiary rounded animate-pulse" /></td>
                </tr>
              ))
            ) : Object.keys(config).length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-text-muted">暂无配置数据</td>
              </tr>
            ) : (
              Object.entries(config).map(([key, value]) => (
                <tr key={key} className="border-b border-border-primary/50 hover:bg-bg-tertiary/30 transition-colors">
                  <td className="px-4 py-3 text-text-secondary font-mono text-sm whitespace-nowrap">{key}</td>
                  <td className="px-4 py-3 text-text-primary font-mono text-sm break-all">{value}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
