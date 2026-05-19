// OrdersContractsPage.tsx - 订单合约
import { Coins, FileText, Shield } from 'lucide-react'
import StatCard from '../../components/shared/StatCard'

const ORDER_CONTRACTS = [
  { name: 'JointOrder', label: '联合订单', addr: '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0', desc: '多方协作订单匹配' },
  { name: 'ZKCredential', label: 'ZK 凭证', addr: '0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874', desc: '零知识身份凭证' },
  { name: 'VIBCollaboration', label: '协作引擎', addr: '0xe568c56f467E27Cb38d4B132B02318C81EC29D78', desc: 'Agent 间收益分配' },
  { name: 'AssetVault', label: '资产金库', addr: '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897', desc: '资产托管与结算' },
  { name: 'AgentRegistry', label: 'Agent 注册表', addr: '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6', desc: 'Agent 身份注册' },
  { name: 'VIBIdentity', label: '身份合约', addr: '0x978eddDf11728B4e6A6C461D8806eD5f4339D466', desc: '链上身份与信誉' },
]

export default function OrdersContractsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary font-rajdhani">订单 & 协作合约</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <StatCard title="联合订单合约" value="JointOrder" icon={FileText} color="primary" />
        <StatCard title="协作引擎" value="VIBCollaboration" icon={Coins} color="info" />
        <StatCard title="Agent 注册" value="AgentRegistry" icon={Shield} color="warning" />
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-primary bg-bg-tertiary">
              <th className="text-left px-4 py-3 text-text-muted font-normal">名称</th>
              <th className="text-left px-4 py-3 text-text-muted font-normal">描述</th>
              <th className="text-left px-4 py-3 text-text-muted font-normal">合约地址</th>
              <th className="text-right px-4 py-3 text-text-muted font-normal">操作</th>
            </tr>
          </thead>
          <tbody>
            {ORDER_CONTRACTS.map(c => (
              <tr key={c.name} className="border-b border-border-primary/50 hover:bg-bg-tertiary/30">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-text-muted shrink-0" />
                    <span className="text-text-primary font-medium">{c.label}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-text-muted text-xs">{c.desc}</td>
                <td className="px-4 py-3 font-mono text-xs text-text-muted">
                  <span className="font-mono">{c.addr.slice(0, 6)}...{c.addr.slice(-4)}</span>
                </td>
                <td className="px-4 py-3 text-right">
                  <a
                    href={`https://sepolia.basescan.org/address/${c.addr}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline text-xs"
                  >
                    Basescan ↗
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 协作引擎统计 */}
      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
          <h3 className="text-text-primary font-rajdhani font-semibold mb-4">协作引擎 (VIBCollaboration)</h3>
          <div className="space-y-3">
            {[
              ['合约地址', '0xe568c56f467E27Cb38d4B132B02318C81EC29D78'],
              ['状态', '● 活跃'],
              ['协作类型', '多方收益分配'],
              ['安全机制', '零知识证明 + 乐观确认'],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between py-2 border-b border-border-primary/30 last:border-0">
                <span className="text-text-muted text-sm">{label}</span>
                <span className="text-text-primary text-sm font-mono text-xs">{value}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-bg-secondary rounded-xl border border-border-primary p-6">
          <h3 className="text-text-primary font-rajdhani font-semibold mb-4">资产金库 (AssetVault)</h3>
          <div className="space-y-3">
            {[
              ['合约地址', '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897'],
              ['状态', '● 活跃'],
              ['托管标准', 'ERC-20 + ERC-721'],
              ['结算方式', 'T+1 自动结算'],
            ].map(([label, value]) => (
              <div key={label} className="flex justify-between py-2 border-b border-border-primary/30 last:border-0">
                <span className="text-text-muted text-sm">{label}</span>
                <span className="text-text-primary text-sm font-mono text-xs">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
