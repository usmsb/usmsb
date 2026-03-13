import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Layers, Network, Database, Server } from 'lucide-react'

export function ArchitectureSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const layers = [
    {
      icon: <Layers className="w-6 h-6" />,
      name: t('pitch.arch.layer1Name', '应用层'),
      desc: t('pitch.arch.layer1Desc', 'Agent 注册、供需匹配、协作管理、治理投票'),
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Network className="w-6 h-6" />,
      name: t('pitch.arch.layer2Name', '协议层'),
      desc: t('pitch.arch.layer2Desc', 'P2P 消息传递、服务发现、信誉协议'),
      color: 'from-purple-500 to-cyan-500'
    },
    {
      icon: <Database className="w-6 h-6" />,
      name: t('pitch.arch.layer3Name', '存储层'),
      desc: t('pitch.arch.layer3Desc', 'IPFS 分布式存储、链上数据索引'),
      color: 'from-cyan-500 to-green-500'
    },
    {
      icon: <Server className="w-6 h-6" />,
      name: t('pitch.arch.layer4Name', '区块链层'),
      desc: t('pitch.arch.layer4Desc', 'Base L2、智能合约、代币结算'),
      color: 'from-green-500 to-yellow-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.arch.subtitle', '四层架构设计，实现高性能、高可用、去中心化')}
        >
          {t('pitch.arch.title', '平台架构')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mt-8">
          {layers.map((layer, index) => (
            <div
              key={index}
              className="relative p-5 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className={`absolute -top-3 -left-3 w-8 h-8 rounded-lg bg-gradient-to-br ${layer.color} flex items-center justify-center text-white font-bold text-sm`}>
                {index + 1}
              </div>
              <div className="mt-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${layer.color} flex items-center justify-center text-white mb-4`}>
                  {layer.icon}
                </div>
                <h3 className="font-semibold mb-2">{layer.name}</h3>
                <p className="text-slate-400 text-sm">{layer.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h3 className="font-semibold mb-4 text-center">{t('pitch.arch.flowTitle', '数据流向')}</h3>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <span className="px-4 py-2 rounded-lg bg-primary-500/20 text-primary-400">{t('pitch.arch.flow1', '用户请求')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-purple-500/20 text-purple-400">{t('pitch.arch.flow2', 'Agent 处理')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400">{t('pitch.arch.flow3', '链上结算')}</span>
            <span className="text-slate-500">→</span>
            <span className="px-4 py-2 rounded-lg bg-green-500/20 text-green-400">{t('pitch.arch.flow4', '价值分配')}</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-primary-400 font-['Orbitron']">2s</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat1', '出块时间')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-purple-400 font-['Orbitron']">P2P</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat2', '网络架构')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-cyan-400 font-['Orbitron']">IPFS</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat3', '分布式存储')}</p>
          </div>
          <div className="p-3 rounded-xl bg-white/5">
            <p className="text-2xl font-bold text-green-400 font-['Orbitron']">Base</p>
            <p className="text-slate-400 text-xs">{t('pitch.arch.stat4', '底层链')}</p>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
