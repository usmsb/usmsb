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
      <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-neon-blue to-neon-purple font-cyber">
        运行时配置
      </h1>

      <div className="card hologram overflow-hidden">
        <div className="px-4 py-3 border-b border-neon-blue/20 bg-cyber-dark/50">
          <h3 className="text-neon-blue font-cyber font-semibold">当前配置</h3>
        </div>
        <table className="w-full text-sm">
          <tbody>
            {isLoading ? (
              [...Array(6)].map((_, i) => (
                <tr key={i} className="border-b border-neon-blue/10">
                  <td className="px-4 py-3"><div className="h-4 w-24 bg-cyber-dark rounded animate-pulse" /></td>
                  <td className="px-4 py-3"><div className="h-4 w-48 bg-cyber-dark rounded animate-pulse" /></td>
                </tr>
              ))
            ) : Object.keys(config).length === 0 ? (
              <tr>
                <td className="px-4 py-8 text-center text-gray-500">暂无配置数据</td>
              </tr>
            ) : (
              Object.entries(config).map(([key, value]) => (
                <tr key={key} className="border-b border-neon-blue/10 hover:bg-cyber-dark/30 transition-colors">
                  <td className="px-4 py-3 text-neon-blue font-mono text-sm whitespace-nowrap">{key}</td>
                  <td className="px-4 py-3 text-gray-200 font-mono text-sm break-all">{value}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
