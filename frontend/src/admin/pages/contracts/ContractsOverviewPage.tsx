// ContractsOverviewPage.tsx - 合约总览
import { ExternalLink } from 'lucide-react'

const ALL_CONTRACTS = [
  { category: 'Core', items: [
    { label: 'VIBEToken', addr: '0x93C52dF000317e12F891474B46d8B05652430bDC', note: 'ERC-20 代币' },
    { label: 'VIBStaking', addr: '0x1901Ab56eA38cBeFc7a3F0Ed188B7108d27f4c05', note: '质押合约' },
    { label: 'VIBGovernance', addr: '0x27475aea1eEba485005B1717a35a7D411d144a1d', note: '治理合约' },
  ]},
  { category: 'Rewards', items: [
    { label: 'VIBBuilderReward', addr: '0x397Faf7D727db190fB677362B15c091f1d94F7b3', note: 'Builder 奖励' },
    { label: 'VIBDevReward', addr: '0x1a5E99b52e87E718906e8516fDD9c8775Ee0351E', note: '开发者奖励' },
    { label: 'VIBNodeReward', addr: '0xc417b180F3b743A51e86c16A8319Eac353fDC29b', note: '节点奖励' },
    { label: 'VIBOutputReward', addr: '0x7b3CEB40CFb093e66EcD5b49F835586Ba7Ef428b', note: '输出奖励' },
    { label: 'VIBDividend', addr: '0xa820F9E9Caa90e405452Fc3f24DC5DF7f7d70E9D', note: '分红合约' },
  ]},
  { category: 'Ecosystem', items: [
    { label: 'VIBInfrastructurePool', addr: '0xFc2943d6D426D4D6433944e1ADa4D475F3552500', note: '基础设施池' },
    { label: 'VIBEcosystemPool', addr: '0x20A25378DB87a94E19A8b51ED638F67d6e9BfE06', note: '生态池' },
    { label: 'VIBReserve', addr: '0x56AbAf5fc5d58c92C0A51F79251BF3A3002f4263', note: '储备金' },
    { label: 'VIBProtocolFund', addr: '0x0F39011e7E542D939C1dce40754a86b01BB3fA5a', note: '协议基金' },
    { label: 'VIBVesting', addr: '0x4d3008550fc164ccf0e1C0C4f666E77FC14dE924', note: '代币归属' },
  ]},
  { category: 'Identity & Registry', items: [
    { label: 'VIBIdentity', addr: '0x978eddDf11728B4e6A6C461D8806eD5f4339D466', note: '身份合约' },
    { label: 'AgentRegistry', addr: '0xC5AbAE9f580C48D645bDE9904712891AE8FcDec6', note: 'Agent 注册' },
    { label: 'ZKCredential', addr: '0x59EE17f1E914ba2de89F080CF44FC46Ee46DF874', note: 'ZK 凭证' },
  ]},
  { category: 'Market & Orders', items: [
    { label: 'PriceOracle', addr: '0x20306509a6b2f0b56ad55C193b4505CA5E62bc48', note: '价格预言机' },
    { label: 'JointOrder', addr: '0x55f4b49c9C269Fccf6d90e16304654b7F69138d0', note: '联合订单' },
    { label: 'VIBCollaboration', addr: '0xe568c56f467E27Cb38d4B132B02318C81EC29D78', note: '协作引擎' },
    { label: 'AssetVault', addr: '0x0F5C6Ae463f78aD30De1C9c6BF180423F0A39897', note: '资产金库' },
  ]},
  { category: 'Points & Delegation', items: [
    { label: 'VIBContributionPoints', addr: '0x60D9244bF262bF85Fd3057C95Ca00fEa1622f3E5', note: '贡献积分' },
    { label: 'VIBGovernanceDelegation', addr: '0x47428bAB428966B32F246a3e9456f10dc70141A5', note: '治理委托' },
    { label: 'VIBVEPoints', addr: '0xB2b56dce955ab200E0c1888C22Ac711803e607F1', note: 'VE Points' },
  ]},
]

export default function ContractsOverviewPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary font-rajdhani">合约总览</h1>
        <span className="text-text-muted text-sm">{ALL_CONTRACTS.reduce((s, c) => s + c.items.length, 0)} 个合约</span>
      </div>

      <div className="bg-bg-secondary rounded-xl border border-border-primary p-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-text-secondary text-sm">Base Sepolia</span>
        </div>
        <span className="text-text-muted text-xs">Chain ID: 84532</span>
        <a
          href="https://sepolia.basescan.org"
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary hover:underline text-xs ml-auto"
        >
          Basescan ↗
        </a>
      </div>

      {ALL_CONTRACTS.map(group => (
        <div key={group.category} className="bg-bg-secondary rounded-xl border border-border-primary overflow-hidden">
          <div className="px-4 py-3 border-b border-border-primary bg-bg-tertiary">
            <h3 className="text-text-primary font-rajdhani font-semibold">{group.category}</h3>
          </div>
          <table className="w-full text-sm">
            <tbody>
              {group.items.map((item, i) => (
                <tr key={item.label} className={`border-b border-border-primary/50 last:border-0 hover:bg-bg-tertiary/30 ${i % 2 === 0 ? 'bg-bg-secondary' : 'bg-bg-tertiary/10'}`}>
                  <td className="px-4 py-3">
                    <span className="text-text-primary font-medium">{item.label}</span>
                    <span className="text-text-muted text-xs ml-2">({item.note})</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-text-muted">{item.addr}</td>
                  <td className="px-4 py-3 text-right">
                    <a
                      href={`https://sepolia.basescan.org/address/${item.addr}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-primary hover:underline text-xs"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}
