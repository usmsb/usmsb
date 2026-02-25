import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { Coins, Wallet, Network, ArrowRightLeft } from 'lucide-react'

export function SolutionSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const solutions = [
    {
      icon: <Coins className="w-8 h-8" />,
      title: t('pitch.solution.item1Title', 'VIBE 代币经济'),
      desc: t('pitch.solution.item1Desc', 'VIBE 作为生态系统的核心代币，用于质押、治理、奖励和交易')
    },
    {
      icon: <Wallet className="w-8 h-8" />,
      title: t('pitch.solution.item2Title', 'Agent 智能钱包'),
      desc: t('pitch.solution.item2Desc', '专为 AI Agent 设计的智能合约钱包，支持限额控制和审批流程')
    },
    {
      icon: <Network className="w-8 h-8" />,
      title: t('pitch.solution.item3Title', '去中心化网络'),
      desc: t('pitch.solution.item3Desc', 'P2P 网络架构，无需中心化服务器，数据分布式存储')
    },
    {
      icon: <ArrowRightLeft className="w-8 h-8" />,
      title: t('pitch.solution.item4Title', '供需匹配市场'),
      desc: t('pitch.solution.item4Desc', '智能匹配算法，自动连接服务提供者和需求方')
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.solution.subtitle', 'VIBE 提供完整的解决方案')}
        >
          {t('pitch.solution.title', '解决方案')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          {solutions.map((solution, index) => (
            <div
              key={index}
              className="relative p-6 rounded-2xl bg-gradient-to-br from-green-500/10 to-emerald-500/5 backdrop-blur-sm border border-green-400/20 hover:border-green-400/40 transition-all"
            >
              <div className="flex gap-4">
                <div className="shrink-0 w-14 h-14 rounded-xl bg-green-500/10 flex items-center justify-center text-green-400">
                  {solution.icon}
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2">{solution.title}</h3>
                  <p className="text-slate-400 text-sm">{solution.desc}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-10 p-6 rounded-2xl bg-white/5 border border-white/10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-center md:text-left">
              <p className="text-slate-400 text-sm mb-1">{t('pitch.solution.techStack', '技术栈')}</p>
              <p className="text-white font-medium">Solidity • React • Base L2 • IPFS</p>
            </div>
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-primary-500/20 text-primary-400 text-sm">ERC-20</span>
              <span className="px-3 py-1 rounded-full bg-purple-500/20 text-purple-400 text-sm">SBT</span>
              <span className="px-3 py-1 rounded-full bg-cyan-500/20 text-cyan-400 text-sm">P2P</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
