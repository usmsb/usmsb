import { useTranslation } from 'react-i18next'
import { SlideContainer, SlideContent, SlideTitle } from '../components/SlideContainer'
import { SlideProps } from '../types'
import { TrendingUp, Coins, Server, CheckCircle } from 'lucide-react'

export function ParticipationSlide({ isActive, direction }: SlideProps) {
  const { t } = useTranslation()

  const roles = [
    {
      icon: <TrendingUp className="w-8 h-8" />,
      title: t('pitch.participate.investorTitle', '投资人'),
      subtitle: t('pitch.participate.investorSubtitle', '早期参与，共享成长'),
      benefits: [
        t('pitch.participate.investorB1', '早期投资机会'),
        t('pitch.participate.investorB2', '流动性挖矿奖励'),
        t('pitch.participate.investorB3', '治理投票权'),
      ],
      color: 'from-yellow-500 to-orange-500'
    },
    {
      icon: <Coins className="w-8 h-8" />,
      title: t('pitch.participate.holderTitle', '持币人'),
      subtitle: t('pitch.participate.holderSubtitle', '质押收益，参与治理'),
      benefits: [
        t('pitch.participate.holderB1', '3-10% APY 质押收益'),
        t('pitch.participate.holderB2', '平台手续费分红'),
        t('pitch.participate.holderB3', 'DAO 治理参与权'),
      ],
      color: 'from-primary-500 to-purple-500'
    },
    {
      icon: <Server className="w-8 h-8" />,
      title: t('pitch.participate.nodeTitle', '节点运营者'),
      subtitle: t('pitch.participate.nodeSubtitle', '维护网络，提供服务'),
      benefits: [
        t('pitch.participate.nodeB1', '网络维护奖励'),
        t('pitch.participate.nodeB2', '服务手续费收入'),
        t('pitch.participate.nodeB3', '生态贡献积分'),
      ],
      color: 'from-cyan-500 to-green-500'
    }
  ]

  return (
    <SlideContainer isActive={isActive} direction={direction}>
      <SlideContent>
        <SlideTitle
          subtitle={t('pitch.participate.subtitle', '多种参与方式，共同构建 AI 文明生态')}
        >
          {t('pitch.participate.title', '参与方式')}
        </SlideTitle>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          {roles.map((role, index) => (
            <div
              key={index}
              className="relative p-6 rounded-2xl bg-white/5 border border-white/10 hover:border-primary-400/30 transition-all"
            >
              <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${role.color} flex items-center justify-center text-white mb-4`}>
                {role.icon}
              </div>
              <h3 className="text-xl font-semibold mb-1">{role.title}</h3>
              <p className="text-slate-400 text-sm mb-4">{role.subtitle}</p>
              
              <ul className="space-y-2">
                {role.benefits.map((benefit, i) => (
                  <li key={i} className="flex items-start gap-2 text-slate-300 text-sm">
                    <CheckCircle className="w-4 h-4 text-green-400 shrink-0 mt-0.5" />
                    {benefit}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-primary-500/10 to-purple-500/10 border border-primary-400/20">
          <h4 className="font-semibold mb-4 text-center">{t('pitch.participate.startTitle', '如何开始')}</h4>
          <div className="flex flex-wrap items-center justify-center gap-4 text-sm">
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-primary-500 flex items-center justify-center text-white text-xs">1</span>
              <span>{t('pitch.participate.step1', '连接钱包')}</span>
            </div>
            <span className="text-slate-500 hidden sm:inline">→</span>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white text-xs">2</span>
              <span>{t('pitch.participate.step2', '质押 VIBE')}</span>
            </div>
            <span className="text-slate-500 hidden sm:inline">→</span>
            <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5">
              <span className="w-6 h-6 rounded-full bg-cyan-500 flex items-center justify-center text-white text-xs">3</span>
              <span>{t('pitch.participate.step3', '参与生态')}</span>
            </div>
          </div>
        </div>
      </SlideContent>
    </SlideContainer>
  )
}
